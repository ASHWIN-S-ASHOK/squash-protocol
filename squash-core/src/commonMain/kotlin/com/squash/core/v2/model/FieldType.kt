package com.squash.core.v2.model

/**
 * Type hints for SQUASH v2 binary deserialization.
 *
 * These map to Protobuf wire types, allowing the reader to correctly
 * interpret binary field values without an external schema.
 */
enum class FieldType(val value: Int) {
    UNSPECIFIED(0),

    /** UTF-8 string — wire type 2 (length-delimited). */
    STRING(1),

    /** Signed 64-bit integer — wire type 0 (varint). */
    INT64(2),

    /** IEEE 754 double — wire type 1 (fixed 64-bit). */
    DOUBLE(3),

    /** Boolean (0 or 1) — wire type 0 (varint). */
    BOOL(4),

    /** Raw byte array — wire type 2 (length-delimited). */
    BYTES(5),

    /** Nested SQUASH object — wire type 2 (length-delimited embedded message). */
    EMBEDDED(6);

    companion object {
        fun fromValue(value: Int): FieldType =
            entries.firstOrNull { it.value == value } ?: UNSPECIFIED
    }
}
