package com.squash.ios

import com.squash.core.codec.Base62
import com.squash.core.codec.JsonTransformer
import com.squash.core.dict.DictionaryBuilder
import com.squash.core.dict.DictionaryStore
import com.squash.core.engine.SquashEngine
import com.squash.core.model.SquashDictionary
import com.squash.core.model.SquashEnvelope
import com.squash.core.model.SquashMeta
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

/**
 * iOS bridge layer exposing SQUASH engine functionality to Swift / Objective-C.
 *
 * This class provides a simplified API surface suitable for consumption from
 * iOS applications via Kotlin/Native framework exports. All methods use
 * primitive types and strings to avoid Kotlin-specific type exposure.
 *
 * Usage from Swift:
 * ```swift
 * let bridge = SquashIosBridge()
 * let encoded = bridge.encode(jsonString: rawJson, schemaName: "user")
 * let decoded = bridge.decode(envelopeString: encoded)
 * ```
 */
class SquashIosBridge {

    private val engine = SquashEngine()
    private val binaryEngine = com.squash.core.v2.engine.BinarySquashEngine()
    private val json = Json { ignoreUnknownKeys = true }

    /**
     * Encodes a JSON string into an SQUASH envelope string.
     *
     * @param jsonString The original JSON payload as a string.
     * @param schemaName The schema name for dictionary lookup/creation.
     * @param clientDictId The client's cached dictionary ID, if any.
     * @return The SQUASH envelope as a JSON string.
     */
    fun encode(jsonString: String, schemaName: String, clientDictId: String? = null): String {
        val element = json.parseToJsonElement(jsonString)
        val envelope = engine.encode(element, schemaName, clientDictId)
        return engine.envelopeToString(envelope)
    }

    /**
     * Decodes an SQUASH envelope string back to the original JSON string.
     *
     * @param envelopeString The SQUASH envelope as a JSON string.
     * @return The expanded original JSON as a string.
     */
    fun decode(envelopeString: String): String {
        val expanded = engine.decodeFromString(envelopeString)
        return json.encodeToString(JsonElement.serializer(), expanded)
    }

    /**
     * Encodes a JSON string into an SQUASH v2 binary frame.
     */
    fun encodeBinary(jsonString: String, schemaName: String, clientDictId: String? = null): ByteArray {
        val element = json.parseToJsonElement(jsonString)
        return binaryEngine.toBinaryFrame(element, schemaName, clientDictId)
    }

    /**
     * Decodes an SQUASH v2 binary frame back to original JSON string.
     */
    fun decodeBinary(frameBytes: ByteArray): String {
        val result = binaryEngine.fromBinaryFrame(frameBytes)
        return json.encodeToString(JsonElement.serializer(), result.data)
    }

    /**
     * Returns the cached dictionary ID for a schema, or null.
     *
     * @param schemaName The schema name to look up.
     * @return The dictId string, or null if not cached.
     */
    fun getCachedDictId(schemaName: String): String? {
        return engine.dictStore.getDictId(schemaName)
    }

    /**
     * Clears all cached dictionaries.
     */
    fun clearDictionaries() {
        engine.dictStore.clear()
    }

    /**
     * Returns the SQUASH header name for dict ID negotiation.
     */
    fun getDictIdHeaderName(): String = "X-SQUASH-DictId"

    /**
     * Returns the SQUASH Accept-Encoding value.
     */
    fun getAcceptEncodingValue(): String = "squash"
}
