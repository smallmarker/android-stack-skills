package com.example.standard.network

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import okhttp3.Call
import okhttp3.EventListener
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okhttp3.mockwebserver.SocketPolicy
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import java.io.Closeable
import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.logging.Handler
import java.util.logging.LogRecord
import java.util.logging.Logger

class NetworkSecurityTest {
    // Generated only in test memory. Both hosts and ports are independently checked by the client.
    private class TlsServers : Closeable {
        private val firstCertificate = certificate()
        private val secondCertificate = certificate()
        val trusted = server(firstCertificate)
        val other = server(secondCertificate)
        private val clientCertificates = HandshakeCertificates.Builder()
            .addTrustedCertificate(firstCertificate.certificate)
            .addTrustedCertificate(secondCertificate.certificate).build()

        fun client(
            server: MockWebServer = trusted,
            tokens: TokenProvider = TokenProvider { "test-token" },
            headers: Map<String, String> = emptyMap(),
        ): OkHttpClient = HttpClientFactory.client(NetworkConfig(server.url("/").toString(), headers = headers), tokens)
            .newBuilder().sslSocketFactory(clientCertificates.sslSocketFactory(), clientCertificates.trustManager).build()

        override fun close() {
            trusted.close()
            other.close()
        }

        companion object {
            private fun certificate() = HeldCertificate.Builder().commonName("localhost")
                .addSubjectAlternativeName("localhost").addSubjectAlternativeName("127.0.0.1").build()

            private fun server(certificate: HeldCertificate): MockWebServer = MockWebServer().apply {
                val tls = HandshakeCertificates.Builder().heldCertificate(certificate).build()
                useHttps(tls.sslSocketFactory(), false)
                start()
            }
        }
    }

    private interface WriteApi {
        @POST("commands") suspend fun submit(@Body body: Map<String, Int>): Response<Unit>
    }

    private fun take(server: MockWebServer): RecordedRequest =
        requireNotNull(server.takeRequest(5, TimeUnit.SECONDS)) { "Expected request did not arrive" }

    private fun assertNoRequest(server: MockWebServer) {
        assertNull(server.takeRequest(150, TimeUnit.MILLISECONDS))
        assertEquals(0, server.requestCount)
    }

    private fun write(server: MockWebServer, method: String): Request = Request.Builder()
        .url(server.url("/commands"))
        .method(method, if (method == "DELETE") null else "{\"amount\":1}".toRequestBody())
        .build()

    private fun assertWrite(server: MockWebServer, method: String) {
        val request = take(server)
        assertEquals(method, request.method)
        assertEquals("/commands", request.path)
        assertEquals(if (method == "DELETE") "" else "{\"amount\":1}", request.body.readUtf8())
        assertNull(server.takeRequest(150, TimeUnit.MILLISECONDS))
        assertEquals(1, server.requestCount)
    }

    @Test fun trustedHttpsReceivesOnlyConfiguredCredentials() {
        TlsServers().use { tls ->
            val client = tls.client(headers = mapOf("X-Api-Key" to "test-key"))
            repeat(2) {
                tls.trusted.enqueue(MockResponse().setHeader("Set-Cookie", "session=response-secret; Secure"))
                client.newCall(Request.Builder().url(tls.trusted.url("/profile"))
                    .header("Authorization", "inherited-secret").header("Cookie", "session=request-secret")
                    .header("Proxy-Authorization", "proxy-secret").header("Cookie2", "legacy-cookie")
                    .header("Host", "untrusted.example").build()).execute().use { response ->
                    assertEquals(200, response.code)
                }
                val received = take(tls.trusted)
                assertEquals("Bearer test-token", received.getHeader("Authorization"))
                assertEquals("test-key", received.getHeader("X-Api-Key"))
                assertNull(received.getHeader("Cookie"))
                assertNull(received.getHeader("Proxy-Authorization"))
                assertNull(received.getHeader("Cookie2"))
                assertEquals("localhost:${tls.trusted.port}", (received.getHeader(":authority") ?: received.getHeader("Host")))
            }
            assertEquals(2, tls.trusted.requestCount)
            assertNoRequest(tls.other)
        }
    }

    @Test fun authenticatedClientRejectsForeignPortHostAndSchemeBeforeSending() {
        TlsServers().use { tls ->
            MockWebServer().use { cleartext ->
                cleartext.start()
                val client = tls.client(headers = mapOf("X-Api-Key" to "test-key"))
                for (url in listOf(tls.other.url("/"), tls.trusted.url("/").newBuilder().host("127.0.0.1").build(),
                    tls.trusted.url("/").newBuilder().scheme("http").build(), cleartext.url("/"))) {
                    tls.other.enqueue(MockResponse())
                    tls.trusted.enqueue(MockResponse())
                    cleartext.enqueue(MockResponse())
                    assertThrows(IOException::class.java) {
                        client.newCall(Request.Builder().url(url).header("Authorization", "inherited-secret")
                            .header("Cookie", "session=request-secret").header("X-Api-Key", "caller-secret").build()).execute().close()
                    }
                }
                assertNoRequest(tls.trusted)
                assertNoRequest(tls.other)
                assertNoRequest(cleartext)
            }
        }
    }

    @Test fun independentThirdPartyClientHasNoInheritedAuthenticationOrCookies() {
        TlsServers().use { tls ->
            val authenticated = tls.client(headers = mapOf("X-Api-Key" to "test-key"))
            val thirdParty = tls.client(tls.other, TokenProvider { null })
            tls.trusted.enqueue(MockResponse())
            authenticated.newCall(Request.Builder().url(tls.trusted.url("/profile")).build()).execute().close()
            assertEquals("Bearer test-token", take(tls.trusted).getHeader("Authorization"))
            tls.other.enqueue(MockResponse())
            thirdParty.newCall(Request.Builder().url(tls.other.url("/public"))
                .header("Authorization", "inherited-secret").header("Cookie", "session=request-secret").build()).execute().close()
            val received = take(tls.other)
            assertEquals("/public", received.path)
            assertNull(received.getHeader("Authorization"))
            assertNull(received.getHeader("Cookie"))
            assertNull(received.getHeader("X-Api-Key"))
            assertEquals(1, tls.other.requestCount)
        }
    }

    @Test fun redirectsStayVisibleForSameOriginForeignHostPortAndDowngrade() {
        TlsServers().use { tls ->
            MockWebServer().use { cleartext ->
                cleartext.start()
                val client = tls.client(headers = mapOf("X-Api-Key" to "test-key"))
                val destinations = listOf(tls.trusted.url("/next"), tls.other.url("/next"),
                    tls.trusted.url("/next").newBuilder().host("127.0.0.1").build(), cleartext.url("/next"))
                for (destination in destinations) {
                    for (status in listOf(301, 302, 303, 307, 308)) {
                        tls.trusted.enqueue(MockResponse().setResponseCode(status).setHeader("Location", destination))
                        client.newCall(Request.Builder().url(tls.trusted.url("/start")).build()).execute().use {
                            assertEquals(status, it.code)
                        }
                        val received = take(tls.trusted)
                        assertEquals("/start", received.path)
                        assertEquals("Bearer test-token", received.getHeader("Authorization"))
                        assertNull(received.getHeader("Cookie"))
                    }
                }
                assertEquals(20, tls.trusted.requestCount)
                assertNull(tls.trusted.takeRequest(150, TimeUnit.MILLISECONDS))
                assertNoRequest(tls.other)
                assertNoRequest(cleartext)
            }
        }
    }

    @Test fun defaultTrustManagerRejectsTestCertificates() {
        TlsServers().use { tls ->
            val client = HttpClientFactory.client(NetworkConfig(tls.trusted.url("/").toString()))
            assertThrows(IOException::class.java) {
                client.newCall(Request.Builder().url(tls.trusted.url("/")).build()).execute().close()
            }
            assertNoRequest(tls.trusted)
        }
    }

    @Test fun writesAreNotReplayedForHttpFollowUps() {
        for (method in listOf("POST", "PUT", "PATCH", "DELETE")) {
            for (status in listOf(401, 407, 408, 421, 503)) {
                TlsServers().use { tls ->
                    tls.trusted.enqueue(MockResponse().setResponseCode(status).setHeader("Retry-After", "0"))
                    tls.trusted.enqueue(MockResponse())
                    val client = tls.client()
                    // A direct 407 without an HTTP proxy is a protocol error in OkHttp.
                    if (status == 407) {
                        assertThrows(IOException::class.java) { client.newCall(write(tls.trusted, method)).execute().close() }
                    } else {
                        client.newCall(write(tls.trusted, method)).execute().use { assertEquals(status, it.code) }
                    }
                    assertWrite(tls.trusted, method)
                    assertNoRequest(tls.other)
                    println("write method=$method status=$status received=1")
                }
            }
        }
    }

    @Test fun connectionRetryFlagAloneStillAllows503ReplayInOkHttp412() {
        TlsServers().use { tls ->
            // Dependency control: preserve TLS trust, remove the production origin/write policy.
            val client = tls.client().newBuilder().apply { interceptors().clear() }
                .retryOnConnectionFailure(false).build()
            tls.trusted.enqueue(MockResponse().setResponseCode(503).setHeader("Retry-After", "0"))
            tls.trusted.enqueue(MockResponse())
            client.newCall(write(tls.trusted, "POST")).execute().use { assertEquals(200, it.code) }
            repeat(2) {
                val received = take(tls.trusted)
                assertEquals("POST", received.method)
                assertEquals("/commands", received.path)
                assertEquals("{\"amount\":1}", received.body.readUtf8())
            }
            assertEquals(2, tls.trusted.requestCount)
            println("OkHttp control retryOnConnectionFailure=false POST received=2")
        }
    }

    @Test fun writeRedirectsKeepMethodBodyAndSingleExecution() {
        for (method in listOf("POST", "PUT", "PATCH", "DELETE")) {
            for (status in listOf(301, 302, 303, 307, 308)) {
                TlsServers().use { tls ->
                    tls.trusted.enqueue(MockResponse().setResponseCode(status).setHeader("Location", tls.other.url("/changed")))
                    tls.client().newCall(write(tls.trusted, method)).execute().use { assertEquals(status, it.code) }
                    assertWrite(tls.trusted, method)
                    assertNoRequest(tls.other)
                    println("write method=$method redirect=$status source=1 target=0")
                }
            }
        }
    }

    @Test fun writeTimeoutAndLostResponseDoNotResubmit() {
        for (policy in listOf(SocketPolicy.NO_RESPONSE, SocketPolicy.DISCONNECT_AFTER_REQUEST)) {
            TlsServers().use { tls ->
                tls.trusted.enqueue(MockResponse().setSocketPolicy(policy))
                tls.trusted.enqueue(MockResponse())
                val client = tls.client().newBuilder().readTimeout(1, TimeUnit.SECONDS)
                    .callTimeout(5, TimeUnit.SECONDS).build()
                assertThrows(IOException::class.java) { client.newCall(write(tls.trusted, "POST")).execute().close() }
                assertWrite(tls.trusted, "POST")
                println("write failure=$policy received=1")
            }
        }
    }

    @Test fun disconnectDuringWriteBodyDoesNotReplayPartialPayload() {
        TlsServers().use { tls ->
            val payload = "x".repeat(64 * 1024)
            tls.trusted.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_DURING_REQUEST_BODY))
            tls.trusted.enqueue(MockResponse())
            val request = Request.Builder().url(tls.trusted.url("/commands")).post(payload.toRequestBody()).build()
            assertThrows(IOException::class.java) { tls.client().newCall(request).execute().close() }
            val received = take(tls.trusted)
            assertEquals("POST", received.method)
            assertEquals("/commands", received.path)
            assertTrue(received.bodySize in 1 until payload.length.toLong())
            assertNull(tls.trusted.takeRequest(150, TimeUnit.MILLISECONDS))
            assertEquals(1, tls.trusted.requestCount)
            println("write partial-body received=1 bytes=${received.bodySize}")
        }
    }

    @Test fun writeConnectionFailureBeforeTlsDoesNotStartAnotherConnection() {
        TlsServers().use { tls ->
            tls.trusted.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))
            tls.trusted.enqueue(MockResponse())
            var attempts = 0
            val client = tls.client().newBuilder().eventListener(object : EventListener() {
                override fun connectStart(call: Call, inetSocketAddress: java.net.InetSocketAddress, proxy: java.net.Proxy) { attempts++ }
            }).build()
            assertThrows(IOException::class.java) { client.newCall(write(tls.trusted, "POST")).execute().close() }
            assertEquals(1, attempts)
            val recorded = take(tls.trusted)
            assertEquals("", recorded.requestLine)
            assertEquals(1, tls.trusted.requestCount)
            assertNull(tls.trusted.takeRequest(150, TimeUnit.MILLISECONDS))
            println("write pre-TLS connections=1 HTTP-executions=0")
        }
    }

    @Test fun cancelledHttpsWriteStopsCallWithoutRetryOrResult() = runBlocking {
        TlsServers().use { tls ->
            val cancelled = CountDownLatch(1)
            val client = tls.client().newBuilder().eventListener(object : EventListener() {
                override fun callFailed(call: Call, ioe: IOException) {
                    if (call.isCanceled()) cancelled.countDown()
                }
            }).build()
            val service = Retrofit.Builder().baseUrl(tls.trusted.url("/")).client(client)
                .addNetworkJsonConverter().build().create(WriteApi::class.java)
            tls.trusted.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
            tls.trusted.enqueue(MockResponse())
            var published = false
            val task = async(start = CoroutineStart.UNDISPATCHED) {
                safeEmptyApiResponse { service.submit(mapOf("amount" to 1)) }
                published = true
            }
            try {
                val received = take(tls.trusted)
                assertEquals("POST", received.method)
                assertEquals("/commands", received.path)
                assertEquals("{\"amount\":1}", received.body.readUtf8())
                task.cancel()
                try { task.await(); fail("Cancellation swallowed") } catch (_: CancellationException) { }
                assertTrue(cancelled.await(5, TimeUnit.SECONDS))
                assertFalse(published)
                assertNull(tls.trusted.takeRequest(150, TimeUnit.MILLISECONDS))
                assertEquals(1, tls.trusted.requestCount)
                println("cancelled write received=1 result-published=false")
            } finally { task.cancel() }
        }
    }

    @Test fun factoryDoesNotLogCredentialsCookiesOrBodies() {
        val records = mutableListOf<String>()
        val logger = Logger.getLogger("okhttp3")
        val handler = object : Handler() {
            override fun publish(record: LogRecord) {
                // MockWebServer is a test server whose request logging is outside the client policy.
                if (!record.loggerName.orEmpty().startsWith("okhttp3.mockwebserver")) {
                    synchronized(records) { records += record.message.orEmpty() }
                }
            }
            override fun flush() = Unit
            override fun close() = Unit
        }
        logger.addHandler(handler)
        try {
            TlsServers().use { tls ->
                val client = tls.client(headers = mapOf("X-Api-Key" to "key-secret"))
                tls.trusted.enqueue(MockResponse().setHeader("Set-Cookie", "session=response-secret"))
                client.newCall(Request.Builder().url(tls.trusted.url("/commands?private=query-secret"))
                    .header("Cookie", "session=cookie-secret").post("body-secret".toRequestBody()).build()).execute().close()
                val received = take(tls.trusted)
                assertEquals("Bearer test-token", received.getHeader("Authorization"))
                assertEquals("key-secret", received.getHeader("X-Api-Key"))
                assertEquals("body-secret", received.body.readUtf8())
                assertEquals(1, tls.trusted.requestCount)
                assertTrue(client.networkInterceptors.isEmpty())
                assertTrue(client.interceptors.none { it.javaClass.name.contains("HttpLoggingInterceptor") })
            }
        } finally { logger.removeHandler(handler) }
        val output = synchronized(records) { records.joinToString("\n") }
        for (secret in listOf("test-token", "key-secret", "response-secret", "cookie-secret", "body-secret", "query-secret")) {
            assertFalse("Credential found in client log", output.contains(secret))
        }
    }
}
