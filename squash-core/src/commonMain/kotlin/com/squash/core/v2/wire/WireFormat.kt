package com.squash.core.v2.wire

/**
 * Protobuf wire format constants and field tag encoding utilities.
 *
 * Wire types define how values are serialized on the wire:
 * - VARINT (0): Variable-length integers (int32, int64, bool, enum)
 * - FIXED64 (1): 8-byte values (double, fixed64)
 * - LENGTH_DELIMITED (2): Length-prefixed data (string, bytes, embedded messages)
 * - FIXED32 (5): 4-byte values (float, fixed32)
 *
 * Field tags combine the field number and wire type:
 * ```
 * tag = (field_number << 3) | wire_type
 * ```
 */
object WireFormat {

    /** Wire type 0: Varint — variable-length integers. */
    const val WIRE_TYPE_VARINT = 0

    /** Wire type 1: 64-bit — fixed 8-byte values (double). */
    const val WIRE_TYPE_FIXED64 = 1

    /** Wire type 2: Length-delimited — strings, bytes, embedded messages. */
    const val WIRE_TYPE_LENGTH_DELIMITED = 2

    /** Wire type 5: 32-bit — fixed 4-byte values (float). */
    const val WIRE_TYPE_FIXED32 = 5

    /**
     * Encodes a field tag from a field number and wire type.
     *
     * @param fieldNumber The 1-based field number.
     * @param wireType The wire type constant.
     * @return The encoded tag value.
     */
    fun makeTag(fieldNumber: Int, wireType: Int): Int {
        return (fieldNumber shl 3) or wireType
    }

    /**
     * Extracts the field number from a tag.
     */
    fun fieldNumber(tag: Int): Int = tag ushr 3

    /**
     * Extracts the wire type from a tag.
     */
    fun wireType(tag: Int): Int = tag and 0x07

    /**
     * Returns the Protobuf wire type for a given SQUASH FieldType.
     */
    fun wireTypeForFieldType(fieldType: Int): Int {
        return when (fieldType) {
            1 -> WIRE_TYPE_LENGTH_DELIMITED  // TYPE_STRING
            2 -> WIRE_TYPE_VARINT            // TYPE_INT64
            3 -> WIRE_TYPE_FIXED64           // TYPE_DOUBLE
            4 -> WIRE_TYPE_VARINT            // TYPE_BOOL
            5 -> WIRE_TYPE_LENGTH_DELIMITED  // TYPE_BYTES
            6 -> WIRE_TYPE_LENGTH_DELIMITED  // TYPE_EMBEDDED
            else -> WIRE_TYPE_LENGTH_DELIMITED // Default to length-delimited
        }
    }
}
