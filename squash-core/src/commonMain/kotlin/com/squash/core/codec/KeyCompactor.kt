package com.squash.core.codec

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Flattens nested JSON keys into dot-notation paths and assigns Base62 short codes.
 *
 * Given a JSON structure like:
 * ```json
 * { "user": { "name": "Ashwin", "address": { "city": "Mumbai" } } }
 * ```
 *
 * This produces a mapping:
 * ```
 * "a" → "user.name"
 * "b" → "user.address.city"
 * ```
 *
 * Leaf keys are collected in depth-first order and assigned sequential Base62 codes.
 */
object KeyCompactor {

    /**
     * Extracts all unique leaf key paths from a [JsonElement] in depth-first order.
     *
     * @param element The JSON tree to scan.
     * @param prefix  Dot-notation prefix for nested keys (used during recursion).
     * @return Ordered list of unique dot-notation key paths.
     */
    fun extractKeyPaths(element: JsonElement, prefix: String = ""): List<String> {
        val paths = mutableListOf<String>()
        collectPaths(element, prefix, paths, mutableSetOf())
        return paths
    }

    private fun collectPaths(
        element: JsonElement,
        prefix: String,
        paths: MutableList<String>,
        seen: MutableSet<String>,
    ) {
        when (element) {
            is JsonObject -> {
                for ((key, value) in element) {
                    val fullPath = if (prefix.isEmpty()) key else "$prefix.$key"
                    when (value) {
                        is JsonObject -> collectPaths(value, fullPath, paths, seen)
                        is JsonArray -> {
                            // For arrays, scan the first object element to discover keys
                            val firstObj = value.filterIsInstance<JsonObject>().firstOrNull()
                            if (firstObj != null) {
                                collectPaths(firstObj, fullPath, paths, seen)
                            } else {
                                // Array of primitives — treat the array key itself as a leaf
                                if (seen.add(fullPath)) paths.add(fullPath)
                            }
                        }
                        else -> {
                            if (seen.add(fullPath)) paths.add(fullPath)
                        }
                    }
                }
            }
            is JsonArray -> {
                val firstObj = element.filterIsInstance<JsonObject>().firstOrNull()
                if (firstObj != null) {
                    collectPaths(firstObj, prefix, paths, seen)
                }
            }
            else -> {
                if (prefix.isNotEmpty() && seen.add(prefix)) {
                    paths.add(prefix)
                }
            }
        }
    }

    /**
     * Builds a Base62 short-key → original-key-path mapping for the given key paths.
     *
     * @param keyPaths Ordered list of dot-notation key paths.
     * @return Map of Base62 short key → original key path.
     */
    fun buildMapping(keyPaths: List<String>): Map<String, String> {
        val keys = Base62.generateKeys(keyPaths.size)
        return keys.zip(keyPaths).toMap()
    }
}
