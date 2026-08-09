Benchmarkpackage com.squash.core.v2.model

/**
 * SQUASH v2 binary dictionary.
 *
 * Maps dense integer field tags (1-based) to canonical JSON key paths,
 * with optional type hints for each field.
 *
 * Example:
 * ```
 * dictId       = "user_v2"
 * fieldMappings = { 1 → "user.name", 2 → "user.email", 3 → "user.address.city" }
 * typeHints     = { 1 → STRING, 2 → STRING, 3 → STRING }
 * ```
 *
 * Field tags 1–15 encode as single-byte Varints, making the most common fields
 * extremely space-efficient on the wire.
 *
 * @property dictId       Unique dictionary identifier.
 * @property version      Monotonically increasing version for cache invalidation.
 * @property fieldMappings Field tag (1-based UInt) → canonical JSON key path.
 * @property typeHints     Field tag → [FieldType] for binary deserialization.
 */
data class BinaryDictionary(
    val dictId: String,
    val version: Int,
    val fieldMappings: Map<Int, String>,
    val typeHints: Map<Int, FieldType> = emptyMap(),
    val valueDictionary: List<String> = emptyList(),
) {
    /** Reverse mapping: JSON key path → field tag. Used during encoding. */
    val reverseMappings: Map<String, Int> by lazy {
        fieldMappings.entries.associate { (tag, path) -> path to tag }
    }

    /** Reverse mapping: String value → index. Used for string interning during encoding. */
    val reverseValueDictionary: Map<String, Int> by lazy {
        valueDictionary.withIndex().associate { it.value to it.index }
    }

    /** Schema name extracted from dictId. */
    val schemaName: String
        get() = dictId.substringBeforeLast("_v")

    /** Number of fields in this dictionary. */
    val fieldCount: Int get() = fieldMappings.size

    /**
     * Returns the type hint for a field, defaulting to STRING if not specified.
     */
    fun typeFor(fieldTag: Int): FieldType =
        typeHints[fieldTag] ?: FieldType.STRING
}
