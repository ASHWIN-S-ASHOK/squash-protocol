package com.squash.core.dict

import com.squash.core.codec.KeyCompactor
import com.squash.core.model.SquashDictionary
import kotlinx.serialization.json.JsonElement

/**
 * Builds SQUASH dictionaries from sample JSON payloads.
 *
 * The builder scans a representative JSON document to discover all leaf key paths,
 * then assigns Base62 short codes to produce a versioned [SquashDictionary].
 *
 * Usage:
 * ```kotlin
 * val dict = DictionaryBuilder.build(
 *     schemaName = "user",
 *     version = 1,
 *     sampleJson = parseJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")
 * )
 * // dict.mapping == { "a": "name", "b": "email" }
 * ```
 */
object DictionaryBuilder {

    /**
     * Builds a dictionary from a sample JSON element.
     *
     * @param schemaName Logical schema name (e.g., `"user"`, `"product"`).
     * @param version    Dictionary version number (monotonically increasing).
     * @param sampleJson A representative JSON document whose structure defines the schema.
     * @return A new [SquashDictionary] with Base62-encoded key mappings.
     */
    fun build(schemaName: String, version: Int, sampleJson: JsonElement): SquashDictionary {
        val keyPaths = KeyCompactor.extractKeyPaths(sampleJson)
        val mapping = KeyCompactor.buildMapping(keyPaths)
        return SquashDictionary(
            dictId = "${schemaName}_v$version",
            version = version,
            mapping = mapping,
        )
    }

    /**
     * Builds a dictionary from an explicit list of key paths.
     *
     * @param schemaName Logical schema name.
     * @param version    Dictionary version number.
     * @param keyPaths   Ordered list of dot-notation key paths.
     * @return A new [SquashDictionary].
     */
    fun buildFromPaths(schemaName: String, version: Int, keyPaths: List<String>): SquashDictionary {
        val mapping = KeyCompactor.buildMapping(keyPaths)
        return SquashDictionary(
            dictId = "${schemaName}_v$version",
            version = version,
            mapping = mapping,
        )
    }
}
