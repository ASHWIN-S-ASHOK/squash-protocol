package com.squash.core.codec

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject

/**
 * Bidirectional JSON tree transformer that compacts and expands JSON payloads
 * using an SQUASH dictionary mapping.
 *
 * **Compact**: Replaces original nested keys with Base62 short codes and flattens
 * the structure into a single-level object.
 *
 * **Expand**: Restores the original nested structure from a compacted flat object
 * using the dictionary mapping.
 */
object JsonTransformer {

    /**
     * Compacts a full JSON tree into a flat object with Base62 short keys.
     *
     * Input:
     * ```json
     * { "user": { "name": "Ashwin", "address": { "city": "Mumbai" } } }
     * ```
     *
     * With dictionary `{ "a": "user.name", "b": "user.address.city" }`:
     * ```json
     * { "a": "Ashwin", "b": "Mumbai" }
     * ```
     *
     * @param original The original JSON element to compact.
     * @param reverseMapping Original key path → Base62 short key.
     * @return Compacted flat [JsonElement].
     */
    fun compact(original: JsonElement, reverseMapping: Map<String, String>): JsonElement {
        return when (original) {
            is JsonObject -> compactObject(original, reverseMapping)
            is JsonArray -> compactArray(original, reverseMapping)
            else -> original
        }
    }

    private fun compactObject(obj: JsonObject, reverseMapping: Map<String, String>): JsonElement {
        val flatEntries = mutableMapOf<String, JsonElement>()
        flattenAndCompact(obj, "", reverseMapping, flatEntries)
        return buildJsonObject {
            flatEntries.forEach { (key, value) -> put(key, value) }
        }
    }

    private fun flattenAndCompact(
        element: JsonElement,
        prefix: String,
        reverseMapping: Map<String, String>,
        result: MutableMap<String, JsonElement>,
    ) {
        when (element) {
            is JsonObject -> {
                for ((key, value) in element) {
                    val fullPath = if (prefix.isEmpty()) key else "$prefix.$key"
                    when (value) {
                        is JsonObject -> flattenAndCompact(value, fullPath, reverseMapping, result)
                        is JsonArray -> {
                            val shortKey = reverseMapping[fullPath]
                            if (shortKey != null) {
                                // Array of primitives — compact the key, keep the array value
                                result[shortKey] = value
                            } else {
                                // Array of objects — compact each element
                                val compacted = compactArray(value, reverseMapping, fullPath)
                                // Find a short key for the array itself, or use original
                                val arrayShortKey = reverseMapping[fullPath] ?: fullPath
                                result[arrayShortKey] = compacted
                            }
                        }
                        else -> {
                            val shortKey = reverseMapping[fullPath]
                            if (shortKey != null) {
                                result[shortKey] = value
                            } else {
                                // Key not in dictionary — preserve as-is
                                result[fullPath] = value
                            }
                        }
                    }
                }
            }
            else -> {
                val shortKey = reverseMapping[prefix]
                if (shortKey != null) {
                    result[shortKey] = element
                }
            }
        }
    }

    private fun compactArray(
        array: JsonArray,
        reverseMapping: Map<String, String>,
        parentPath: String = "",
    ): JsonArray {
        return buildJsonArray {
            for (item in array) {
                when (item) {
                    is JsonObject -> {
                        val flat = mutableMapOf<String, JsonElement>()
                        flattenAndCompact(item, parentPath, reverseMapping, flat)
                        add(buildJsonObject {
                            flat.forEach { (k, v) -> put(k, v) }
                        })
                    }
                    else -> add(item)
                }
            }
        }
    }

    /**
     * Expands a compacted flat JSON object back into its original nested structure.
     *
     * Input:
     * ```json
     * { "a": "Ashwin", "b": "Mumbai" }
     * ```
     *
     * With dictionary `{ "a": "user.name", "b": "user.address.city" }`:
     * ```json
     * { "user": { "name": "Ashwin", "address": { "city": "Mumbai" } } }
     * ```
     *
     * @param compacted The compacted JSON element.
     * @param mapping   Base62 short key → original key path.
     * @return Expanded nested [JsonElement].
     */
    fun expand(compacted: JsonElement, mapping: Map<String, String>): JsonElement {
        return when (compacted) {
            is JsonObject -> expandObject(compacted, mapping)
            is JsonArray -> expandArray(compacted, mapping)
            else -> compacted
        }
    }

    private fun expandObject(obj: JsonObject, mapping: Map<String, String>): JsonElement {
        val nested = mutableMapOf<String, Any>()

        for ((shortKey, value) in obj) {
            val originalPath = mapping[shortKey] ?: shortKey
            val parts = originalPath.split(".")
            setNestedValue(nested, parts, value, mapping)
        }

        return buildNestedJsonElement(nested)
    }

    private fun expandArray(array: JsonArray, mapping: Map<String, String>): JsonArray {
        return buildJsonArray {
            for (item in array) {
                add(expand(item, mapping))
            }
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun setNestedValue(
        root: MutableMap<String, Any>,
        parts: List<String>,
        value: JsonElement,
        mapping: Map<String, String>,
    ) {
        var current = root
        for (i in 0 until parts.size - 1) {
            current = current.getOrPut(parts[i]) { mutableMapOf<String, Any>() } as MutableMap<String, Any>
        }
        // Expand arrays of objects recursively
        val expandedValue = when (value) {
            is JsonArray -> expandArray(value, mapping)
            else -> value
        }
        current[parts.last()] = expandedValue
    }

    @Suppress("UNCHECKED_CAST")
    private fun buildNestedJsonElement(map: Map<String, Any>): JsonElement {
        return buildJsonObject {
            for ((key, value) in map) {
                when (value) {
                    is Map<*, *> -> put(key, buildNestedJsonElement(value as Map<String, Any>))
                    is JsonElement -> put(key, value)
                }
            }
        }
    }
}
