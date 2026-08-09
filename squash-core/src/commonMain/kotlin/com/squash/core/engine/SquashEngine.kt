package com.squash.core.engine

import com.squash.core.codec.JsonTransformer
import com.squash.core.dict.DictionaryBuilder
import com.squash.core.dict.DictionaryStore
import com.squash.core.model.SquashDictionary
import com.squash.core.model.SquashEnvelope
import com.squash.core.model.SquashMeta
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/**
 * Main SQUASH protocol engine — the single entry point for encoding and decoding
 * JSON payloads using the Hybrid JSON Compact Protocol.
 *
 * The engine manages a [DictionaryStore] for caching dictionaries and provides
 * methods for:
 * - **Encoding**: Converting a full JSON payload into a compact SQUASH envelope.
 * - **Decoding**: Restoring the original JSON from an SQUASH envelope.
 * - **Dict sync**: Determining whether a dictionary should be included in responses.
 *
 * Thread Safety: The engine itself is stateless beyond the [DictionaryStore].
 * Concurrent access to the store should be externally synchronized if needed.
 */
class SquashEngine(
    val dictStore: DictionaryStore = DictionaryStore(),
    val json: Json = Json { ignoreUnknownKeys = true },
) {

    /**
     * Encodes a JSON payload into an SQUASH envelope.
     *
     * If a dictionary for the given schema already exists in the store, it is reused.
     * Otherwise, a new dictionary is built from the payload structure.
     *
     * @param originalJson The original JSON payload to compact.
     * @param schemaName   The logical schema name (e.g., `"user"`).
     * @param clientDictId The client's currently cached dictId, if any.
     *                     Used to decide whether to include `__dict` in the envelope.
     * @return An [SquashEnvelope] containing the compacted payload and metadata.
     */
    fun encode(
        originalJson: JsonElement,
        schemaName: String,
        clientDictId: String? = null,
    ): SquashEnvelope {
        // Get or build dictionary
        val dictionary = dictStore.get(schemaName)
            ?: DictionaryBuilder.build(schemaName, 1, originalJson).also { dictStore.put(it) }

        // Compact the payload
        val compactedData = JsonTransformer.compact(originalJson, dictionary.reverseMapping)

        // Determine if we need to send the dictionary
        val includeDict = shouldIncludeDict(dictionary.dictId, clientDictId)

        return SquashEnvelope(
            meta = SquashMeta(
                version = 1,
                dictId = dictionary.dictId,
                encoding = "map",
            ),
            dict = if (includeDict) dictionary.mapping else null,
            data = compactedData,
        )
    }

    /**
     * Encodes a JSON payload using a pre-existing dictionary.
     *
     * @param originalJson The original JSON payload.
     * @param dictionary   The dictionary to use for compaction.
     * @param clientDictId The client's cached dictId, if any.
     * @return An [SquashEnvelope].
     */
    fun encodeWithDict(
        originalJson: JsonElement,
        dictionary: SquashDictionary,
        clientDictId: String? = null,
    ): SquashEnvelope {
        dictStore.put(dictionary)
        val compactedData = JsonTransformer.compact(originalJson, dictionary.reverseMapping)
        val includeDict = shouldIncludeDict(dictionary.dictId, clientDictId)

        return SquashEnvelope(
            meta = SquashMeta(
                version = 1,
                dictId = dictionary.dictId,
                encoding = "map",
            ),
            dict = if (includeDict) dictionary.mapping else null,
            data = compactedData,
        )
    }

    /**
     * Decodes an SQUASH envelope back into the original JSON structure.
     *
     * If the envelope contains a `__dict`, it is cached in the store for future use.
     * If no `__dict` is present, the engine looks up the dictionary from the cache.
     *
     * @param envelope The SQUASH envelope to decode.
     * @return The original expanded [JsonElement].
     * @throws IllegalStateException if no dictionary is available for the envelope's dictId.
     */
    fun decode(envelope: SquashEnvelope): JsonElement {
        // If envelope contains a dict, cache it
        val mapping = if (envelope.dict != null) {
            val version = extractVersion(envelope.meta.dictId)
            val dict = SquashDictionary(
                dictId = envelope.meta.dictId,
                version = version,
                mapping = envelope.dict,
            )
            dictStore.put(dict)
            envelope.dict
        } else {
            // Look up from cache
            val cached = dictStore.getByDictId(envelope.meta.dictId)
                ?: throw IllegalStateException(
                    "No dictionary found for dictId '${envelope.meta.dictId}'. " +
                        "The server should have included __dict in the response."
                )
            cached.mapping
        }

        return JsonTransformer.expand(envelope.data, mapping)
    }

    /**
     * Decodes a raw JSON string as an SQUASH envelope.
     *
     * @param jsonString The raw SQUASH JSON string.
     * @return The original expanded [JsonElement].
     */
    fun decodeFromString(jsonString: String): JsonElement {
        val envelope = json.decodeFromString<SquashEnvelope>(jsonString)
        return decode(envelope)
    }

    /**
     * Serializes an SQUASH envelope to a JSON string.
     *
     * @param envelope The envelope to serialize.
     * @return Compact JSON string representation.
     */
    fun envelopeToString(envelope: SquashEnvelope): String {
        return json.encodeToString(SquashEnvelope.serializer(), envelope)
    }

    /**
     * Determines whether the dictionary should be included in the response envelope.
     *
     * The dict is included when:
     * - The client has no cached dict (`clientDictId` is null)
     * - The client's cached dict version doesn't match the server's current version
     *
     * @param serverDictId The server's current dictId.
     * @param clientDictId The client's declared dictId from `X-SQUASH-DictId` header.
     * @return `true` if `__dict` should be included in the envelope.
     */
    fun shouldIncludeDict(serverDictId: String, clientDictId: String?): Boolean {
        if (clientDictId == null) return true
        return clientDictId != serverDictId
    }

    /**
     * Registers a pre-built dictionary in the store.
     *
     * @param dictionary The dictionary to register.
     */
    fun registerDictionary(dictionary: SquashDictionary) {
        dictStore.put(dictionary)
    }

    private fun extractVersion(dictId: String): Int {
        return dictId.substringAfterLast("_v").toIntOrNull() ?: 1
    }
}
