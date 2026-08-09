package com.squash.core.model

/**
 * Represents a versioned SQUASH dictionary that maps Base62 short keys
 * to their original fully-qualified JSON key paths.
 *
 * Example dictionary:
 * ```
 * dictId  = "user_v1"
 * mapping = { "a" → "user.name", "b" → "user.email", "c" → "user.address.city" }
 * ```
 *
 * @property dictId  Unique dictionary identifier in `{schema}_v{version}` format.
 * @property version Monotonically increasing version number for cache invalidation.
 * @property mapping Short-key → original-key-path mapping.
 */
data class SquashDictionary(
    val dictId: String,
    val version: Int,
    val mapping: Map<String, String>,
) {
    /** Reversed mapping: original key path → short key. Used during compaction. */
    val reverseMapping: Map<String, String> by lazy {
        mapping.entries.associate { (short, original) -> original to short }
    }

    /**
     * Returns the schema name portion of the dictId.
     * For `"user_v1"` this returns `"user"`.
     */
    val schemaName: String
        get() = dictId.substringBeforeLast("_v")
}
