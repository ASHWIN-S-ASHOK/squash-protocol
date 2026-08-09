package com.squash.core.v2.engine

import com.squash.core.model.SquashDictionary
import com.squash.core.v2.model.BinaryDictionary
import com.squash.core.v2.model.FieldType
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.longOrNull

/**
 * Translates SQUASH v1 Base62 string dictionaries into SQUASH v2 dense
 * integer field tag dictionaries.
 *
 * The mapper assigns 1-based sequential integer tags to dictionary entries,
 * preserving the same key-path ordering as v1. This ensures:
 *
 * - Fields 1–15 use single-byte Varint tags (most space-efficient)
 * - The mapping is deterministic and reproducible from the same v1 dictionary
 * - v1 ↔ v2 dictionary conversion is lossless
 *
 * Example:
 * ```
 * v1: { "a" → "user.name", "b" → "user.email" }
 * v2: { 1 → "user.name", 2 → "user.email" }
 * ```
 */
object VarintKeyMapper {

    /**
     * Converts a v1 [SquashDictionary] (Base62 keys) to a v2 [BinaryDictionary]
     * (integer field tags).
     *
     * @param v1Dict The v1 dictionary to convert.
     * @param sampleJson Optional sample JSON to infer type hints from.
     * @return A [BinaryDictionary] with 1-based integer field tags.
     */
    fun fromV1Dictionary(
        v1Dict: SquashDictionary,
        sampleJson: JsonElement? = null,
    ): BinaryDictionary {
        // v1 dictionaries are ordered by Base62 key (a, b, c, …)
        // We preserve this order and assign 1-based tags
        val sortedEntries = v1Dict.mapping.entries.sortedBy { it.key }

        val fieldMappings = mutableMapOf<Int, String>()
        val typeHints = mutableMapOf<Int, FieldType>()

        sortedEntries.forEachIndexed { index, (_, keyPath) ->
            val fieldTag = index + 1  // 1-based
            fieldMappings[fieldTag] = keyPath

            // Infer type hint from sample JSON if available
            if (sampleJson != null) {
                val inferredType = inferFieldType(sampleJson, keyPath)
                typeHints[fieldTag] = inferredType
            }
        }

        val valueDictionary = if (sampleJson != null) {
            extractStringValues(sampleJson)
        } else {
            emptyList()
        }

        return BinaryDictionary(
            dictId = v1Dict.dictId,
            version = v1Dict.version,
            fieldMappings = fieldMappings,
            typeHints = typeHints,
            valueDictionary = valueDictionary,
        )
    }

    /**
     * Builds a v2 dictionary directly from key paths.
     *
     * @param schemaName Schema name for the dictionary.
     * @param version    Version number.
     * @param keyPaths   Ordered list of dot-notation key paths.
     * @param sampleJson Optional sample JSON for type inference.
     * @return A [BinaryDictionary].
     */
    fun buildDictionary(
        schemaName: String,
        version: Int,
        keyPaths: List<String>,
        sampleJson: JsonElement? = null,
    ): BinaryDictionary {
        val fieldMappings = mutableMapOf<Int, String>()
        val typeHints = mutableMapOf<Int, FieldType>()

        keyPaths.forEachIndexed { index, keyPath ->
            val fieldTag = index + 1
            fieldMappings[fieldTag] = keyPath

            if (sampleJson != null) {
                typeHints[fieldTag] = inferFieldType(sampleJson, keyPath)
            }
        }

        val valueDictionary = if (sampleJson != null) {
            extractStringValues(sampleJson)
        } else {
            emptyList()
        }

        return BinaryDictionary(
            dictId = "${schemaName}_v$version",
            version = version,
            fieldMappings = fieldMappings,
            typeHints = typeHints,
            valueDictionary = valueDictionary,
        )
    }

    /**
     * Extracts unique string values from sample data up to a limit.
     */
    private fun extractStringValues(json: JsonElement, maxStrings: Int = 127): List<String> {
        val strings = mutableSetOf<String>()

        fun walk(node: JsonElement) {
            if (strings.size >= maxStrings) return
            when (node) {
                is JsonObject -> node.values.forEach { walk(it) }
                is JsonArray -> node.forEach { walk(it) }
                is JsonPrimitive -> {
                    if (node.isString) {
                        strings.add(node.content)
                    }
                }
                is JsonNull -> {}
            }
        }

        walk(json)
        return strings.toList()
    }

    /**
     * Infers the [FieldType] of a value at the given dot-notation path
     * in a JSON tree.
     */
    fun inferFieldType(json: JsonElement, keyPath: String): FieldType {
        val value = resolveJsonPath(json, keyPath) ?: return FieldType.STRING

        return when (value) {
            is JsonPrimitive -> {
                when {
                    value.isString -> FieldType.STRING
                    value.booleanOrNull != null -> FieldType.BOOL
                    value.longOrNull != null -> FieldType.INT64
                    value.doubleOrNull != null -> FieldType.DOUBLE
                    else -> FieldType.STRING
                }
            }
            is JsonObject -> FieldType.EMBEDDED
            is JsonArray -> FieldType.EMBEDDED // Arrays encoded as embedded JSON
            is JsonNull -> FieldType.STRING
            else -> FieldType.STRING
        }
    }

    /**
     * Resolves a dot-notation path in a JSON tree.
     * For `"user.address.city"` in `{"user":{"address":{"city":"Mumbai"}}}`,
     * returns `JsonPrimitive("Mumbai")`.
     */
    private fun resolveJsonPath(json: JsonElement, path: String): JsonElement? {
        val parts = path.split(".")
        var current: JsonElement = json

        for (part in parts) {
            current = when (current) {
                is JsonObject -> current[part] ?: return null
                is JsonArray -> {
                    val firstObj = current.filterIsInstance<JsonObject>().firstOrNull()
                    firstObj?.get(part) ?: return null
                }
                else -> return null
            }
        }

        return current
    }
}
