package com.squash.core.v2.wire

/**
 * Binary frame reader for SQUASH v2 payloads.
 *
 * Reads Protobuf-compatible wire format data: field tags, varints,
 * length-delimited strings/bytes, and fixed-width numbers.
 *
 * Usage:
 * ```kotlin
 * val reader = BinaryReader(bytes)
 * while (!reader.isAtEnd()) {
 *     val tag = reader.readTag()
 *     val fieldNumber = WireFormat.fieldNumber(tag)
 *     val wireType = WireFormat.wireType(tag)
 *     when (wireType) {
 *         WireFormat.WIRE_TYPE_VARINT -> reader.readVarint()
 *         WireFormat.WIRE_TYPE_LENGTH_DELIMITED -> reader.readString()
 *         WireFormat.WIRE_TYPE_FIXED64 -> reader.readDouble()
 *         // ...
 *     }
 * }
 * ```
 */
class BinaryReader(private val data: ByteArray) {

    private var position: Int = 0

    /** Returns true if there are no more bytes to read. */
    fun isAtEnd(): Boolean = position >= data.size

    /** Returns the current read position. */
    fun currentPosition(): Int = position

    /** Returns the number of remaining bytes. */
    fun remaining(): Int = data.size - position

    /**
     * Reads a field tag (varint) and returns the raw tag value.
     * Use [WireFormat.fieldNumber] and [WireFormat.wireType] to decompose.
     */
    fun readTag(): Int {
        if (isAtEnd()) return 0
        return readVarint().toInt()
    }

    /**
     * Reads a varint value from the stream.
     *
     * @return The decoded unsigned long value.
     * @throws IllegalArgumentException if the data is malformed.
     */
    fun readVarint(): Long {
        val result = Varint.decode(data, position)
        position += result.bytesRead
        return result.value
    }

    /**
     * Reads a length-delimited string field.
     * Expects: <varint_length> <utf8_bytes>
     */
    fun readString(): String {
        val length = readVarint().toInt()
        require(position + length <= data.size) {
            "String length $length exceeds available data at position $position"
        }
        val str = data.decodeToString(position, position + length)
        position += length
        return str
    }

    /**
     * Reads a length-delimited byte array field.
     * Expects: <varint_length> <raw_bytes>
     */
    fun readBytes(): ByteArray {
        val length = readVarint().toInt()
        require(position + length <= data.size) {
            "Bytes length $length exceeds available data at position $position"
        }
        val bytes = data.copyOfRange(position, position + length)
        position += length
        return bytes
    }

    /**
     * Reads a boolean value (varint 0 or 1).
     */
    fun readBool(): Boolean = readVarint() != 0L

    /**
     * Reads a double (fixed 64-bit, little-endian).
     */
    fun readDouble(): Double {
        require(position + 8 <= data.size) {
            "Not enough data for double at position $position"
        }
        var bits = 0L
        for (i in 0 until 8) {
            bits = bits or ((data[position + i].toLong() and 0xFF) shl (i * 8))
        }
        position += 8
        return Double.fromBits(bits)
    }

    /**
     * Reads a float (fixed 32-bit, little-endian).
     */
    fun readFloat(): Float {
        require(position + 4 <= data.size) {
            "Not enough data for float at position $position"
        }
        var bits = 0
        for (i in 0 until 4) {
            bits = bits or ((data[position + i].toInt() and 0xFF) shl (i * 8))
        }
        position += 4
        return Float.fromBits(bits)
    }

    /**
     * Skips a field value based on its wire type.
     * Useful for forward-compatibility when encountering unknown fields.
     */
    fun skipField(wireType: Int) {
        when (wireType) {
            WireFormat.WIRE_TYPE_VARINT -> readVarint()
            WireFormat.WIRE_TYPE_FIXED64 -> {
                require(position + 8 <= data.size) { "Not enough data to skip fixed64" }
                position += 8
            }
            WireFormat.WIRE_TYPE_LENGTH_DELIMITED -> {
                val length = readVarint().toInt()
                require(position + length <= data.size) { "Not enough data to skip length-delimited" }
                position += length
            }
            WireFormat.WIRE_TYPE_FIXED32 -> {
                require(position + 4 <= data.size) { "Not enough data to skip fixed32" }
                position += 4
            }
            else -> throw IllegalArgumentException("Unknown wire type: $wireType")
        }
    }
}
