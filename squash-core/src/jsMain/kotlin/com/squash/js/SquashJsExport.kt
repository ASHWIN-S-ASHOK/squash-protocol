@file:OptIn(ExperimentalJsExport::class)

package com.squash.js

import com.squash.core.engine.SquashEngine
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

/**
 * JavaScript/TypeScript bindings for the SQUASH engine.
 *
 * All methods accept and return plain strings to maintain clean interop
 * with JavaScript consumers. These are exported as a JS module via
 * `@JsExport` for use in Node.js or browser environments.
 *
 * Usage from TypeScript:
 * ```typescript
 * import { SquashJsEngine } from 'squash-core';
 *
 * const engine = new SquashJsEngine();
 * const envelope = engine.encode('{"name":"Ashwin"}', 'user');
 * const original = engine.decode(envelope);
 * ```
 */
@JsExport
class SquashJsEngine {

    private val engine = SquashEngine()
    private val binaryEngine = com.squash.core.v2.engine.BinarySquashEngine()
    private val json = Json { ignoreUnknownKeys = true }

    /**
     * Encodes a JSON string into an SQUASH envelope string.
     *
     * @param jsonString The original JSON payload.
     * @param schemaName The schema name for dictionary management.
     * @param clientDictId Optional client dictionary ID for sync.
     * @return SQUASH envelope as a JSON string.
     */
    fun encode(jsonString: String, schemaName: String, clientDictId: String? = null): String {
        val element = json.parseToJsonElement(jsonString)
        val envelope = engine.encode(element, schemaName, clientDictId)
        return engine.envelopeToString(envelope)
    }

    /**
     * Decodes an SQUASH envelope string back to original JSON.
     *
     * @param envelopeString The SQUASH envelope JSON string.
     * @return The expanded original JSON string.
     */
    fun decode(envelopeString: String): String {
        val expanded = engine.decodeFromString(envelopeString)
        return json.encodeToString(JsonElement.serializer(), expanded)
    }

    /**
     * Encodes a JSON string into an SQUASH v2 binary frame (Int8Array in JS).
     */
    fun encodeBinary(jsonString: String, schemaName: String, clientDictId: String? = null): ByteArray {
        val element = json.parseToJsonElement(jsonString)
        return binaryEngine.toBinaryFrame(element, schemaName, clientDictId)
    }

    /**
     * Decodes an SQUASH v2 binary frame (Int8Array) back to original JSON string.
     */
    fun decodeBinary(frameBytes: ByteArray): String {
        val result = binaryEngine.fromBinaryFrame(frameBytes)
        return json.encodeToString(JsonElement.serializer(), result.data)
    }

    /**
     * Returns the cached dictionary ID for a given schema.
     *
     * @param schemaName Schema name to look up.
     * @return The dictId or null.
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
}
