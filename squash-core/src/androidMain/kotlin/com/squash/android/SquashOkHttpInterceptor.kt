package com.squash.android

import com.squash.core.engine.SquashEngine
import com.squash.core.v2.engine.BinarySquashEngine
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody

/**
 * OkHttp interceptor with dual-mode SQUASH v1 (JSON) and v2 (binary) support.
 *
 * **Request side:**
 * - Adds `Accept: application/squash+proto, application/squash+json` to declare
 *   both binary and JSON SQUASH support (binary preferred).
 * - Adds `X-SQUASH-DictId: {dictId}` if a cached dictionary exists.
 *
 * **Response side:**
 * - `Content-Type: application/squash+proto` → decodes via [BinarySquashEngine]
 * - `Content-Type: application/squash+json` or `Content-Encoding: squash` → decodes via [SquashEngine] (v1)
 * - All other responses pass through unchanged.
 *
 * Usage:
 * ```kotlin
 * val client = OkHttpClient.Builder()
 *     .addInterceptor(SquashOkHttpInterceptor(v1Engine, v2Engine))
 *     .build()
 * ```
 *
 * @param engine The shared v1 [SquashEngine] instance.
 * @param binaryEngine Optional v2 [BinarySquashEngine] instance. If null, binary mode is disabled.
 * @param defaultSchemaName Optional default schema name for dict lookup on requests.
 * @param preferBinary Whether to prefer binary mode when both are available.
 */
class SquashOkHttpInterceptor(
    private val engine: SquashEngine = SquashEngine(),
    private val binaryEngine: BinarySquashEngine? = BinarySquashEngine(),
    private val defaultSchemaName: String? = null,
    private val preferBinary: Boolean = true,
) : Interceptor {

    companion object {
        const val HEADER_ACCEPT = "Accept"
        const val HEADER_ACCEPT_ENCODING = "Accept-Encoding"
        const val HEADER_CONTENT_TYPE = "Content-Type"
        const val HEADER_CONTENT_ENCODING = "Content-Encoding"
        const val HEADER_SQUASH_DICT_ID = "X-SQUASH-DictId"

        const val ENCODING_SQUASH = "squash"
        const val CONTENT_TYPE_SQUASH_PROTO = "application/squash+proto"
        const val CONTENT_TYPE_SQUASH_JSON = "application/squash+json"

        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        // --- Request modification ---
        val originalRequest = chain.request()
        val requestBuilder = originalRequest.newBuilder()

        // Set Accept header for content negotiation
        if (binaryEngine != null) {
            val accept = if (preferBinary) {
                "$CONTENT_TYPE_SQUASH_PROTO, $CONTENT_TYPE_SQUASH_JSON"
            } else {
                "$CONTENT_TYPE_SQUASH_JSON, $CONTENT_TYPE_SQUASH_PROTO"
            }
            requestBuilder.header(HEADER_ACCEPT, accept)
        }
        // Also keep v1 Accept-Encoding for backward compatibility
        requestBuilder.header(HEADER_ACCEPT_ENCODING, ENCODING_SQUASH)

        // Attach cached dictId if available
        val schemaName = originalRequest.header(HEADER_SQUASH_DICT_ID) ?: defaultSchemaName
        if (schemaName != null) {
            val dictId = engine.dictStore.getDictId(schemaName)
                ?: binaryEngine?.getDictId(schemaName)
            if (dictId != null) {
                requestBuilder.header(HEADER_SQUASH_DICT_ID, dictId)
            }
        }

        val response = chain.proceed(requestBuilder.build())

        // --- Response decoding ---
        val contentType = response.header(HEADER_CONTENT_TYPE) ?: ""
        val contentEncoding = response.header(HEADER_CONTENT_ENCODING) ?: ""

        return when {
            // v2 binary mode
            contentType.contains(CONTENT_TYPE_SQUASH_PROTO) && binaryEngine != null -> {
                decodeBinaryResponse(response)
            }
            // v1 JSON mode (via Content-Type)
            contentType.contains(CONTENT_TYPE_SQUASH_JSON) -> {
                decodeJsonResponse(response)
            }
            // v1 JSON mode (via Content-Encoding, backward compat)
            contentEncoding == ENCODING_SQUASH -> {
                decodeJsonResponse(response)
            }
            // Not an SQUASH response
            else -> response
        }
    }

    /**
     * Decodes a v2 binary SQUASH response.
     */
    private fun decodeBinaryResponse(response: Response): Response {
        val body = response.body ?: return response
        val binaryData = body.bytes()

        return try {
            val result = binaryEngine!!.fromBinaryFrame(binaryData)
            val expandedString = engine.json.encodeToString(
                kotlinx.serialization.json.JsonElement.serializer(),
                result.data,
            )

            response.newBuilder()
                .removeHeader(HEADER_CONTENT_TYPE)
                .removeHeader(HEADER_CONTENT_ENCODING)
                .header(HEADER_CONTENT_TYPE, "application/json; charset=utf-8")
                .body(expandedString.toResponseBody(JSON_MEDIA_TYPE))
                .build()
        } catch (e: Exception) {
            response.newBuilder()
                .body(binaryData.toResponseBody(body.contentType()))
                .build()
        }
    }

    /**
     * Decodes a v1 JSON SQUASH response.
     */
    private fun decodeJsonResponse(response: Response): Response {
        val body = response.body ?: return response
        val squashJson = body.string()

        return try {
            val expandedJson = engine.decodeFromString(squashJson)
            val expandedString = engine.json.encodeToString(
                kotlinx.serialization.json.JsonElement.serializer(),
                expandedJson,
            )

            response.newBuilder()
                .removeHeader(HEADER_CONTENT_ENCODING)
                .removeHeader(HEADER_CONTENT_TYPE)
                .header(HEADER_CONTENT_TYPE, "application/json; charset=utf-8")
                .body(expandedString.toResponseBody(JSON_MEDIA_TYPE))
                .build()
        } catch (e: Exception) {
            response.newBuilder()
                .body(squashJson.toResponseBody(body.contentType()))
                .build()
        }
    }
}
