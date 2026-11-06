package com.example.lightweight.network

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import okhttp3.Call
import okhttp3.EventListener
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.ResponseBody.Companion.toResponseBody
import okhttp3.Protocol
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.Response
import retrofit2.http.POST
import java.io.IOException
import java.net.ServerSocket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class NetworkTest {
    private interface EmptyApi {
        @POST("acknowledge") suspend fun acknowledge(): Response<Unit>
    }

    private fun retrofit(server: MockWebServer, client: OkHttpClient = OkHttpClient()): Retrofit =
        Retrofit.Builder().baseUrl(server.url("/")).client(client).addNetworkJsonConverter().build()

    private fun repository(server: MockWebServer, client: OkHttpClient = OkHttpClient()): UserRepository =
        UserRepository(retrofit(server, client).create(UserApi::class.java))

    @Test fun success() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("""{"id":1,"name":"Ada"}"""))
            assertEquals(ApiResult.Success(User(1, "Ada")), repository(server).getUser())
        }
    }

    @Test fun requiredBodyRejectsNoContent() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setResponseCode(204))
            assertEquals(ApiResult.Failure(ApiError.MissingBody), repository(server).getUser())
        }
    }

    @Test fun requiredFieldsRejectEmptyObject() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("{}"))
            assertEquals(
                ApiResult.Failure(ApiError.InvalidField("id", FieldViolation.MissingOrNull)),
                repository(server).getUser(),
            )
        }
    }

    @Test fun requiredBodyRejectsEmptyOrNullJson() = runBlocking {
        MockWebServer().use { server ->
            for (body in listOf("", "null")) {
                server.enqueue(MockResponse().setBody(body))
                assertEquals(ApiResult.Failure(ApiError.MissingBody), repository(server).getUser())
            }
        }
    }

    @Test fun requiredBodyRejectsResetContent() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setResponseCode(205))
            assertEquals(ApiResult.Failure(ApiError.MissingBody), repository(server).getUser())
        }
    }

    @Test fun emptyResponseIsExplicitlySupported() = runBlocking {
        MockWebServer().use { server ->
            val service = retrofit(server).create(EmptyApi::class.java)
            server.enqueue(MockResponse().setResponseCode(204))
            assertEquals(ApiResult.Success(Unit), safeEmptyApiResponse(service::acknowledge))
            server.enqueue(MockResponse().setResponseCode(400))
            assertEquals(ApiResult.Failure(ApiError.Http(400)), safeEmptyApiResponse(service::acknowledge))
        }
    }

    @Test fun missingAndNullFieldsAreContractErrors() = runBlocking {
        MockWebServer().use { server ->
            val repo = repository(server)
            for ((body, field) in listOf(
                """{"name":"Ada"}""" to "id",
                """{"id":null,"name":"Ada"}""" to "id",
                """{"id":1}""" to "name",
                """{"id":1,"name":null}""" to "name",
            )) {
                server.enqueue(MockResponse().setBody(body))
                assertEquals(ApiResult.Failure(ApiError.InvalidField(field, FieldViolation.MissingOrNull)), repo.getUser())
            }
        }
    }

    @Test fun wrongFieldTypesAreNotCoerced() = runBlocking {
        MockWebServer().use { server ->
            val repo = repository(server)
            for ((body, field) in listOf(
                """{"id":{}}""" to "id",
                """{"id":"1","name":"Ada"}""" to "id",
                """{"id":1.5,"name":"Ada"}""" to "id",
                """{"id":9223372036854775808,"name":"Ada"}""" to "id",
                """{"id":1,"name":7}""" to "name",
            )) {
                server.enqueue(MockResponse().setBody(body))
                assertEquals(ApiResult.Failure(ApiError.InvalidField(field, FieldViolation.WrongType)), repo.getUser())
            }
        }
    }

    @Test fun domainConstraintsAreEndpointSpecific() = runBlocking {
        MockWebServer().use { server ->
            val repo = repository(server)
            for ((body, field) in listOf(
                """{"id":0,"name":"Ada"}""" to "id",
                """{"id":-1,"name":"Ada"}""" to "id",
                """{"id":1,"name":""}""" to "name",
                """{"id":1,"name":"  "}""" to "name",
            )) {
                server.enqueue(MockResponse().setBody(body))
                assertEquals(ApiResult.Failure(ApiError.InvalidField(field, FieldViolation.Constraint)), repo.getUser())
            }
        }
    }

    @Test fun httpErrors() = runBlocking {
        MockWebServer().use { server ->
            for (code in listOf(400, 401, 500)) {
                server.enqueue(MockResponse().setResponseCode(code).setBody("private"))
                assertEquals(ApiResult.Failure(ApiError.Http(code)), repository(server).getUser())
            }
        }
    }

    @Test fun invalidJson() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("""{"id":1 "name":"Ada"}"""))
            assertEquals(ApiResult.Failure(ApiError.Parsing), repository(server).getUser())
        }
    }

    @Test fun timeout() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("{}").setBodyDelay(1, TimeUnit.SECONDS))
            val client = OkHttpClient.Builder().readTimeout(30, TimeUnit.MILLISECONDS).build()
            assertEquals(ApiResult.Failure(ApiError.Timeout), repository(server, client).getUser())
        }
    }

    @Test fun connectionFailure() = runBlocking {
        val port = ServerSocket(0).use { it.localPort }
        val api = Retrofit.Builder().baseUrl("http://127.0.0.1:$port/")
            .addNetworkJsonConverter().build().create(UserApi::class.java)
        assertEquals(ApiResult.Failure(ApiError.Connection), UserRepository(api).getUser())
    }

    @Test fun tokenHeaders() {
        MockWebServer().use { server ->
            for (token in listOf("test-token", "", null)) {
                server.enqueue(MockResponse())
                val client = OkHttpClient.Builder().addInterceptor(AuthInterceptor(TokenProvider { token }, server.url("/"))).build()
                client.newCall(Request.Builder().url(server.url("/")).build()).execute().close()
                assertEquals(token?.takeIf { it.isNotBlank() }?.let { "Bearer $it" }, server.takeRequest().getHeader("Authorization"))
            }
        }
    }

    @Test fun cancellationPropagates() {
        val cancellation = CancellationException("cancel")
        try {
            runBlocking { safeApiCall<Unit> { throw cancellation } }
            fail("Cancellation swallowed")
        } catch (actual: CancellationException) { assertSame(cancellation, actual) }
    }

    @Test fun alreadyCancelledCallerDoesNotStartRequest() = runBlocking {
        MockWebServer().use { server ->
            var started = false
            val client = OkHttpClient.Builder().eventListener(object : EventListener() {
                override fun callStart(call: Call) { started = true }
            }).build()
            val repo = repository(server, client)
            var cancellationPropagated = false
            val task = launch(start = CoroutineStart.UNDISPATCHED) {
                currentCoroutineContext()[Job]!!.cancel()
                try {
                    repo.getUser()
                    fail("Cancellation swallowed")
                } catch (_: CancellationException) {
                    cancellationPropagated = true
                }
            }
            task.join()
            assertTrue(cancellationPropagated)
            assertFalse(started)
            assertEquals(0, server.requestCount)
        }
    }

    @Test fun cancellingInFlightRequestCancelsCallWithoutPublishingResult() = runBlocking {
        MockWebServer().use { server ->
            val callFailed = CountDownLatch(1)
            val client = OkHttpClient.Builder().eventListener(object : EventListener() {
                override fun callFailed(call: Call, ioe: IOException) {
                    if (call.isCanceled()) callFailed.countDown()
                }
            }).build()
            server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
            val service = retrofit(server, client).create(UserApi::class.java)
            var mapped = false
            var published = false
            val task = async(start = CoroutineStart.UNDISPATCHED) {
                safeApiResponse(service::getUser) {
                    mapped = true
                    ApiResult.Success(Unit)
                }
                published = true
            }
            try {
                assertEquals("/user", server.takeRequest(5, TimeUnit.SECONDS)?.path)
                task.cancel()
                try {
                    task.await()
                    fail("Cancellation swallowed")
                } catch (_: CancellationException) { }
                assertTrue("OkHttp did not fail the cancelled call", callFailed.await(5, TimeUnit.SECONDS))
                assertFalse(mapped)
                assertFalse(published)
            } finally {
                task.cancel()
            }
        }
    }

    @Test fun programmingErrorsPropagate() {
        assertThrows(IllegalStateException::class.java) {
            runBlocking { safeApiCall<Unit> { error("bug") } }
        }
    }

    @Test fun tokenIsNotSentToAnotherOrigin() {
        MockWebServer().use { trusted ->
            MockWebServer().use { other ->
                other.enqueue(MockResponse())
                var tokenReads = 0
                val client = OkHttpClient.Builder().addInterceptor(
                    AuthInterceptor(TokenProvider { tokenReads++; "secret-token" }, trusted.url("/"))
                ).build()
                client.newCall(Request.Builder().url(other.url("/")).build()).execute().close()
                assertNull(other.takeRequest().getHeader("Authorization"))
                assertEquals(0, tokenReads)
            }
        }
    }

    @Test fun cancelledTransportDoesNotBecomeResult() {
        val job = kotlinx.coroutines.Job()
        runBlocking {
            val task = kotlinx.coroutines.CoroutineScope(job).async(start = kotlinx.coroutines.CoroutineStart.UNDISPATCHED) {
                safeApiCall<Unit> {
                    kotlinx.coroutines.currentCoroutineContext()[kotlinx.coroutines.Job]!!.cancel()
                    throw java.io.IOException("transport cancelled")
                }
            }
            try { task.await(); fail("Cancellation swallowed") }
            catch (_: CancellationException) { }
        }
    }

    @Test fun wholeCallTimeout() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setHeadersDelay(1, TimeUnit.SECONDS).setBody("{}"))
            val client = OkHttpClient.Builder().callTimeout(30, TimeUnit.MILLISECONDS).build()
            assertEquals(ApiResult.Failure(ApiError.Timeout), repository(server, client).getUser())
        }
    }

    @Test fun truncatedJsonIsParsingError() = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("{\"id\":"))
            assertEquals(ApiResult.Failure(ApiError.Parsing), repository(server).getUser())
        }
    }

    @Test fun commonHeadersAndTokensAreOriginScoped() {
        val config = NetworkConfig("https://api.example.com/", headers = mapOf("X-Api-Key" to "secret"))
        var tokenReads = 0
        val client = HttpClientFactory.client(config, TokenProvider { tokenReads++; "token" })
            .newBuilder().addInterceptor { chain ->
                val trusted = chain.request().url.host == "api.example.com"
                assertEquals(if (trusted) "secret" else null, chain.request().header("X-Api-Key"))
                assertEquals(if (trusted) "Bearer token" else null, chain.request().header("Authorization"))
                okhttp3.Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1)
                    .code(200).message("OK").body("".toResponseBody()).build()
            }.build()
        client.newCall(Request.Builder().url("https://api.example.com/user").build()).execute().close()
        assertThrows(IOException::class.java) {
            client.newCall(Request.Builder().url("https://other.example.com/user").build()).execute().close()
        }
        assertEquals(1, tokenReads)
    }

    @Test fun productionConfigRequiresHttps() {
        assertThrows(IllegalArgumentException::class.java) { NetworkConfig("http://example.com/") }
        assertThrows(IllegalArgumentException::class.java) { NetworkConfig("https://user:password@example.com/") }
        assertThrows(IllegalArgumentException::class.java) { NetworkConfig("https://example.com/?secret=/") }
        assertThrows(IllegalArgumentException::class.java) { NetworkConfig("https://example.com/", headers = mapOf("Cookie" to "secret")) }
    }
}
