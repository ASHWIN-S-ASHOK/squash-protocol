package com.squash.android

import com.squash.core.engine.SquashEngine
import com.squash.core.model.SquashEnvelope
import kotlinx.serialization.json.JsonElement
import okhttp3.ResponseBody
import retrofit2.Converter
import retrofit2.Retrofit
import java.lang.reflect.Type

/**
 * Retrofit [Converter.Factory] that transparently handles SQUASH-encoded responses.
 *
 * When used with [SquashOkHttpInterceptor], this converter receives already-expanded
 * JSON responses. However, it can also be used standalone to decode SQUASH envelopes
 * directly from response bodies.
 *
 * Usage:
 * ```kotlin
 * val retrofit = Retrofit.Builder()
 *     .baseUrl("https://api.example.com/")
 *     .addConverterFactory(SquashRetrofitConverter.create(engine))
 *     .build()
 * ```
 *
 * @see SquashOkHttpInterceptor for the recommended setup with automatic header negotiation.
 */
class SquashRetrofitConverter private constructor(
    private val engine: SquashEngine,
) : Converter.Factory() {

    companion object {
        /**
         * Creates a new [SquashRetrofitConverter] factory.
         *
         * @param engine The shared [SquashEngine] instance.
         * @return A [Converter.Factory] for Retrofit.
         */
        fun create(engine: SquashEngine = SquashEngine()): SquashRetrofitConverter {
            return SquashRetrofitConverter(engine)
        }
    }

    override fun responseBodyConverter(
        type: Type,
        annotations: Array<out Annotation>,
        retrofit: Retrofit,
    ): Converter<ResponseBody, *>? {
        // Only handle JsonElement return types
        if (type != JsonElement::class.java) {
            return null
        }
        return SquashResponseBodyConverter(engine)
    }

    /**
     * Converter that reads the response body and attempts to decode it as an SQUASH envelope.
     * If the body is not a valid SQUASH envelope, it falls back to parsing as raw JSON.
     */
    private class SquashResponseBodyConverter(
        private val engine: SquashEngine,
    ) : Converter<ResponseBody, JsonElement> {

        override fun convert(value: ResponseBody): JsonElement {
            val bodyString = value.string()
            return try {
                // Try SQUASH decode first
                engine.decodeFromString(bodyString)
            } catch (_: Exception) {
                // Fall back to raw JSON parse
                engine.json.parseToJsonElement(bodyString)
            }
        }
    }
}
