package com.squash.core.codec

/**
 * Base62 key generator for SQUASH dictionary encoding.
 *
 * Generates deterministic short keys in the following order:
 * ```
 * 0  → "a"   ...  25 → "z"
 * 26 → "A"   ...  51 → "Z"
 * 52 → "0"   ...  61 → "9"
 * 62 → "aa"  ...  63 → "ab"  ...  123 → "ba"  ...
 * ```
 *
 * This provides single-character keys for the first 62 fields and
 * two-character keys for up to 62² = 3844 additional fields — more
 * than sufficient for any practical JSON schema.
 */
object Base62 {

    private const val ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    private const val BASE = 62

    /**
     * Converts a zero-based index to a Base62 short key.
     *
     * @param index Zero-based index (0, 1, 2, …).
     * @return The Base62 encoded short key string.
     * @throws IllegalArgumentException if index is negative.
     */
    fun encode(index: Int): String {
        require(index >= 0) { "Index must be non-negative, got $index" }

        if (index < BASE) {
            return ALPHABET[index].toString()
        }

        // For indices >= 62, we generate multi-character keys.
        // Subtract the single-char range, then convert to base-62 digits.
        var remaining = index - BASE
        val chars = mutableListOf<Char>()

        // We need at least 2 characters for the multi-char range
        do {
            chars.add(0, ALPHABET[remaining % BASE])
            remaining /= BASE
        } while (remaining > 0)

        // Prepend leading 'a' to ensure minimum 2 characters
        while (chars.size < 2) {
            chars.add(0, ALPHABET[0])
        }

        return chars.joinToString("")
    }

    /**
     * Generates a list of [count] sequential Base62 keys starting from index 0.
     *
     * @param count Number of keys to generate.
     * @return List of Base62 keys: ["a", "b", …, "z", "A", …, "Z", "0", …, "9", "aa", …]
     */
    fun generateKeys(count: Int): List<String> {
        require(count >= 0) { "Count must be non-negative, got $count" }
        return (0 until count).map { encode(it) }
    }
}
