package com.example.standard.network

import com.google.gson.GsonBuilder
import com.google.gson.JsonElement
import com.google.gson.JsonParseException
import com.google.gson.Strictness
import com.google.gson.annotations.SerializedName
import com.google.gson.stream.MalformedJsonException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import okhttp3.Authenticator
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.ResponseBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.BufferedSink
import retrofit2.Converter
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.Response as HttpResponse
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import java.io.IOException
import java.io.EOFException
import java.io.InterruptedIOException
import java.lang.reflect.Type
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
    data object MissingBody : ApiError
    data class InvalidField(val field: String, val reason: FieldViolation) : ApiError
}

enum class FieldViolation { MissingOrNull, WrongType, Constraint }

/** Catch transport/parse failures only; programming errors remain visible. */
suspend fun <T> safeApiCall(call: suspend () -> T): ApiResult<T> {
    val context = currentCoroutineContext()
    context.ensureActive()
    val result = try {
        ApiResult.Success(call())
    } catch (error: CancellationException) {
        throw error
    } catch (error: HttpException) {
        error.response()?.errorBody()?.close()
        ApiResult.Failure(ApiError.Http(error.code()))
    } catch (error: InterruptedIOException) {
        ApiResult.Failure(ApiError.Timeout)
    } catch (error: JsonParseException) {
        ApiResult.Failure(ApiError.Parsing)
    } catch (error: MalformedJsonException) {
        ApiResult.Failure(ApiError.Parsing)
    } catch (error: EOFException) {
        ApiResult.Failure(ApiError.Parsing)
    } catch (error: IOException) {
        ApiResult.Failure(ApiError.Connection)
    }
    context.ensureActive()
    return result
}

/** Map a successful response that must contain a body. Keep the mapper short and non-blocking. */
suspend fun <Dto : Any, Model> safeApiResponse(
    call: suspend () -> HttpResponse<Dto>,
    mapBody: (Dto) -> ApiResult<Model>,
): ApiResult<Model> = mapApiResponse(call) { body ->
    if (body == null) ApiResult.Failure(ApiError.MissingBody) else mapBody(body)
}

/** For endpoints whose contract allows success without a body. */
suspend fun safeEmptyApiResponse(call: suspend () -> HttpResponse<Unit>): ApiResult<Unit> =
    mapApiResponse(call) { ApiResult.Success(Unit) }

private suspend fun <Dto, Model> mapApiResponse(
    call: suspend () -> HttpResponse<Dto>,
    mapBody: (Dto?) -> ApiResult<Model>,
): ApiResult<Model> {
    val context = currentCoroutineContext()
    val result = when (val transport = safeApiCall(call)) {
        is ApiResult.Failure -> transport
        is ApiResult.Success -> {
            val response = transport.value
            if (response.isSuccessful) {
                context.ensureActive()
                mapBody(response.body())
            } else {
                response.errorBody()?.close()
                ApiResult.Failure(ApiError.Http(response.code()))
            }
        }
    }
    context.ensureActive()
    return result
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
            // Credentials have one owner. Never inherit per-request auth or session cookies.
            removeHeader("Authorization")
            removeHeader("Proxy-Authorization")
            removeHeader("Cookie")
            removeHeader("Cookie2")
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
        require(headers.keys.none { key ->
            listOf("Authorization", "Proxy-Authorization", "Cookie", "Cookie2", "Host").any { it.equals(key, true) }
        }) {
            "Use TokenProvider for authentication; session cookies and Host overrides are unsupported"
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
            .retryOnConnectionFailure(false)
            .authenticator(Authenticator.NONE)
            .proxyAuthenticator(Authenticator.NONE)
            .cookieJar(CookieJar.NO_COOKIES)
            .followRedirects(false)
            .followSslRedirects(false)
            .addInterceptor { chain ->
                val origin = config.baseUrl.toHttpUrl()
                val request = chain.request()
                val url = request.url
                if (url.scheme != origin.scheme || url.host != origin.host || url.port != origin.port) {
                    throw IOException("Request origin is not allowed by this client")
                }
                if (url.username.isNotEmpty() || url.password.isNotEmpty()) {
                    throw IOException("URL credentials are unsupported")
                }
                val scoped = request.newBuilder().removeHeader("Host").apply {
                    config.headers.forEach { (key, value) -> header(key, value) }
                    if (request.method != "GET" && request.method != "HEAD") {
                        val body = request.body ?: "".toRequestBody()
                        // Covers OkHttp follow-ups such as 503 + Retry-After: 0, too.
                        method(request.method, OneShotBody(body))
                    }
                }.build()
                chain.proceed(scoped)
            }
            .addInterceptor(AuthInterceptor(tokens, config.baseUrl.toHttpUrl()))
            .build()

    fun retrofit(config: NetworkConfig, tokens: TokenProvider = TokenProvider { null }): Retrofit =
        Retrofit.Builder().baseUrl(config.baseUrl).client(client(config, tokens))
            .addNetworkJsonConverter().build()
}

/** Default write policy. A caller retrying a new Call is still responsible for business idempotency. */
private class OneShotBody(private val delegate: RequestBody) : RequestBody() {
    override fun contentType() = delegate.contentType()
    override fun contentLength() = delegate.contentLength()
    override fun isOneShot() = true
    override fun isDuplex() = delegate.isDuplex()
    override fun writeTo(sink: BufferedSink) = delegate.writeTo(sink)
}

// Retrofit handles 204/205 itself. A zero-byte 200 also has no JSON to decode.
internal fun Retrofit.Builder.addNetworkJsonConverter(): Retrofit.Builder =
    addConverterFactory(EmptyJsonBodyConverter)
        .addConverterFactory(GsonConverterFactory.create(GsonBuilder().setStrictness(Strictness.STRICT).create()))

private object EmptyJsonBodyConverter : Converter.Factory() {
    override fun responseBodyConverter(
        type: Type,
        annotations: Array<Annotation>,
        retrofit: Retrofit,
    ): Converter<ResponseBody, Any?> {
        val decode = retrofit.nextResponseBodyConverter<Any?>(this, type, annotations)
        return Converter { body ->
            body.use {
                if (it.source().exhausted()) null else decode.convert(it)
            }
        }
    }
}

data class User(val id: Long, val name: String)

/** Wire fields preserve JSON token types so Gson cannot silently coerce them. */
data class UserDto(
    @SerializedName("id") val id: JsonElement? = null,
    @SerializedName("name") val name: JsonElement? = null,
)

interface UserApi {
    @GET("user") suspend fun getUser(): HttpResponse<UserDto>
}

class UserRepository(private val api: UserApi) {
    suspend fun getUser(): ApiResult<User> = safeApiResponse(api::getUser, ::mapUser)
}

// Example contract only: a positive integer ID and a non-blank display name.
private fun mapUser(dto: UserDto): ApiResult<User> {
    val idField = dto.id
    if (idField == null || idField.isJsonNull) return invalidUserField("id", FieldViolation.MissingOrNull)
    if (!idField.isJsonPrimitive || !idField.asJsonPrimitive.isNumber) {
        return invalidUserField("id", FieldViolation.WrongType)
    }
    val id = idField.asString.toLongOrNull() ?: return invalidUserField("id", FieldViolation.WrongType)
    if (id <= 0) return invalidUserField("id", FieldViolation.Constraint)

    val nameField = dto.name
    if (nameField == null || nameField.isJsonNull) return invalidUserField("name", FieldViolation.MissingOrNull)
    if (!nameField.isJsonPrimitive || !nameField.asJsonPrimitive.isString) {
        return invalidUserField("name", FieldViolation.WrongType)
    }
    val name = nameField.asString
    if (name.isBlank()) return invalidUserField("name", FieldViolation.Constraint)
    return ApiResult.Success(User(id, name))
}

private fun invalidUserField(field: String, reason: FieldViolation): ApiResult.Failure =
    ApiResult.Failure(ApiError.InvalidField(field, reason))
