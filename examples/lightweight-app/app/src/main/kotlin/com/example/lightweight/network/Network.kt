package com.example.lightweight.network

import com.google.gson.JsonParseException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import java.io.IOException
import java.io.EOFException
import java.io.InterruptedIOException
import java.util.concurrent.TimeUnit

sealed interface ApiResult<out T> {
    data class Success<T>(val value: T) : ApiResult<T>
    data class Failure(val error: ApiError) : ApiResult<Nothing>
}

sealed interface ApiError {
    data class Http(val code: Int) : ApiError
    data object Timeout : ApiError
    data object Connection : ApiError
    data object Parsing : ApiError
}

/** Catch transport/parse failures only; programming errors remain visible. */
suspend fun <T> safeApiCall(call: suspend () -> T): ApiResult<T> = try {
    ApiResult.Success(call())
} catch (error: CancellationException) {
    throw error
} catch (error: HttpException) {
    ApiResult.Failure(ApiError.Http(error.code()))
} catch (error: InterruptedIOException) {
    currentCoroutineContext().ensureActive()
    ApiResult.Failure(ApiError.Timeout)
} catch (error: JsonParseException) {
    ApiResult.Failure(ApiError.Parsing)
} catch (error: EOFException) {
    currentCoroutineContext().ensureActive()
    ApiResult.Failure(ApiError.Parsing)
} catch (error: IOException) {
    currentCoroutineContext().ensureActive()
    ApiResult.Failure(ApiError.Connection)
}

fun interface TokenProvider {
    /** Non-blocking lookup; never log the returned value. */
    fun token(): String?
}

class AuthInterceptor(private val provider: TokenProvider, private val origin: HttpUrl) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val url = chain.request().url
        val sameOrigin = url.scheme == origin.scheme && url.host == origin.host && url.port == origin.port
        val token = if (sameOrigin) provider.token()?.takeIf { it.isNotBlank() } else null
        val request = chain.request().newBuilder().apply {
            if (token != null) header("Authorization", "Bearer $token")
        }.build()
        return chain.proceed(request)
    }
}

data class NetworkConfig(
    val baseUrl: String,
    val timeoutSeconds: Long = 30,
    val headers: Map<String, String> = emptyMap(),
) {
    init {
        val url = baseUrl.toHttpUrl()
        require(url.isHttps) { "HTTPS base URL required" }
        require(url.username.isEmpty() && url.password.isEmpty()) { "Credentials must not be embedded in URLs" }
        require(url.encodedPath.endsWith("/") && url.query == null && url.fragment == null) {
            "Base URL must end with / and contain no query or fragment"
        }
        require(timeoutSeconds > 0)
        require(headers.keys.none { it.equals("Authorization", true) || it.equals("Cookie", true) }) {
            "Provide credentials through TokenProvider"
        }
    }
}

object HttpClientFactory {
    fun client(config: NetworkConfig, tokens: TokenProvider = TokenProvider { null }): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .callTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder().apply {
                    val origin = config.baseUrl.toHttpUrl()
                    val url = chain.request().url
                    if (url.scheme == origin.scheme && url.host == origin.host && url.port == origin.port) {
                        config.headers.forEach { (key, value) -> header(key, value) }
                    }
                }.build()
                chain.proceed(request)
            }
            .addInterceptor(AuthInterceptor(tokens, config.baseUrl.toHttpUrl()))
            // Do not forward custom credentials to redirected hosts.
            .followRedirects(false)
            .followSslRedirects(false)
            .build()

    fun retrofit(config: NetworkConfig, tokens: TokenProvider = TokenProvider { null }): Retrofit =
        Retrofit.Builder().baseUrl(config.baseUrl).client(client(config, tokens))
            .addConverterFactory(GsonConverterFactory.create()).build()
}

// Illustrative DTO; no universal backend envelope is assumed.
data class User(val id: Long, val name: String)
interface UserApi {
    @GET("user") suspend fun getUser(): User
}
class UserRepository(private val api: UserApi) {
    suspend fun getUser(): ApiResult<User> = safeApiCall { api.getUser() }
}
