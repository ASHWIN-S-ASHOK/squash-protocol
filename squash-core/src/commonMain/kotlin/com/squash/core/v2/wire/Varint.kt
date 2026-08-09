package com.squash.core.v2.wire

/**
 * Unsigned Varint (LEB128) encoder/decoder.
 *
 * Varints are a compact encoding for unsigned integers used in Protocol Buffers.
 * Each byte uses 7 bits for data and 1 bit (MSB) as a continuation flag:
 *
 * ```
 * Value 300 (0x012C):
 *   Byte 1: 1_0101100  (0xAC) — MSB=1 means "more bytes follow"
 *   Byte 2: 0_0000010  (0x02) — MSB=0 means "final byte"
 * ```
 *
 * Size characteristics:
 * - Values 0–127: 1 byte
 * - Values 128–16383: 2 bytes
 * - Values 16384–2097151: 3 bytes
 *
 * This is critical for SQUASH v2: field tags 1–15 encode as single bytes,
 * making the 15 most common fields extremely space-efficient.
 */
object Varint {

    /**
     * Encodes an unsigned integer as a Varint byte sequence.
     *
     * @param value The unsigned value to encode (treated as unsigned).
     * @return ByteArray containing the Varint encoding.
     */
    fun encode(value: Long): ByteArray {
        if (value < 0) {
            // Negative values need 10 bytes in protobuf varint encoding
            return encodeFull(value)
        }

        val bytes = mutableListOf<Byte>()
        var remaining = value

        do {
            var byte = (remaining and 0x7F).toByte()
            remaining = remaining ushr 7
            if (remaining != 0L) {
                byte = (byte.toInt() or 0x80).toByte()
            }
            bytes.add(byte)
        } while (remaining != 0L)

        return bytes.toByteArray()
    }

    /**
     * Encodes an Int as a Varint.
     */
    fun encode(value: Int): ByteArray = encode(value.toLong())

    /**
     * Encodes an unsigned Int as a Varint.
     */
    fun encode(value: UInt): ByteArray = encode(value.toLong())

    /**
     * Decodes a Varint from a byte array starting at the given offset.
     *
     * @param bytes The byte array to read from.
     * @param offset Starting position in the array.
     * @return A [DecodeResult] containing the decoded value and the number of bytes consumed.
     * @throws IllegalArgumentException if the varint is malformed.
     */
    fun decode(bytes: ByteArray, offset: Int = 0): DecodeResult {
        var result = 0L
        var shift = 0
        var pos = offset

        while (pos < bytes.size) {
            val byte = bytes[pos].toInt() and 0xFF
            result = result or ((byte.toLong() and 0x7F) shl shift)
            pos++

            if (byte and 0x80 == 0) {
                return DecodeResult(result, pos - offset)
            }

            shift += 7
            require(shift < 64) { "Varint too long (more than 10 bytes)" }
        }

        throw IllegalArgumentException("Unexpected end of varint at offset $offset")
    }

    private fun encodeFull(value: Long): ByteArray {
        val bytes = ByteArray(10)
        var remaining = value
        for (i in 0 until 10) {
            bytes[i] = ((remaining and 0x7F) or (if (i < 9) 0x80 else 0)).toByte()
            remaining = remaining ushr 7
        }
        return bytes
    }

    /**
     * Result of decoding a Varint.
     *
     * @property value The decoded unsigned integer value.
     * @property bytesRead Number of bytes consumed from the input.
     */
    data class DecodeResult(val value: Long, val bytesRead: Int) {
        /** Convenience accessor for Int values. */
        val intValue: Int get() = value.toInt()
    }
}
