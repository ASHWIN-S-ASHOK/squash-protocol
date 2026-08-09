package com.squash.core.v2.model

/**
 * SQUASH v2 encoding modes.
 *
 * Determines how the payload section of a binary frame is structured.
 */
enum class EncodingType(val value: Int) {
    /** Unspecified — should not appear in valid frames. */
    UNSPECIFIED(0),

    /**
     * Binary Map: each field is tagged with its Varint field number.
     * `tag → value` pairs in Protobuf wire format.
     * This is the primary v2 encoding mode.
     */
    BINARY_MAP(1),

    /**
     * Binary Array: values are packed in dictionary order without individual tags.
     * Requires both sides to have an identical, ordered dictionary.
     * (Future — not implemented in v2.0)
     */
    BINARY_ARRAY(2),

    /**
     * Protobuf Dynamic: full Protobuf message with a dynamically-generated
     * .proto descriptor. Enables zero-copy deserialization on the receiver.
     * (Future — not implemented in v2.0)
     */
    PROTOBUF_DYNAMIC(3);

    companion object {
        fun fromValue(value: Int): EncodingType =
            entries.firstOrNull { it.value == value } ?: UNSPECIFIED
    }
}
