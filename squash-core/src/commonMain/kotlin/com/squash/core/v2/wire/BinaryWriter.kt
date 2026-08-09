package com.squash.core.v2.wire

/**
 * Binary frame writer for SQUASH v2 payloads.
 *
 * Writes Protobuf-compatible wire format data: field tags, varints,
 * length-delimited strings/bytes, and fixed-width numbers.
 *
 * Usage:
 * ```kotlin
 * val writer = BinaryWriter()
 * writer.writeString(1, "Ashwin")     // field 1 = string
 * writer.writeInt64(2, 28)            // field 2 = varint int
 * writer.writeBool(3, true)           // field 3 = bool
 * writer.writeDouble(4, 99.99)        // field 4 = double
 * val bytes = writer.toByteArray()
 * ```
 */
class BinaryWriter {

    private var buffer = ByteArray(256)
    private var offset = 0

    private fun ensureCapacity(size: Int) {
        if (offset + size > buffer.size) {
            var newSize = buffer.size * 2
            while (offset + size > newSize) {
                newSize *= 2
            }
            buffer = buffer.copyOf(newSize)
        }
    }

    /** Writes a tagged string field. */
    fun writeString(fieldNumber: Int, value: String) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
        val bytes = value.encodeToByteArray()
        writeRawVarint(bytes.size.toLong())
        writeRawBytes(bytes)
    }

    /** Writes a tagged int64 (varint) field. */
    fun writeInt64(fieldNumber: Int, value: Long) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_VARINT)
        writeRawVarint(value)
    }

    /** Writes a tagged boolean field (varint 0 or 1). */
    fun writeBool(fieldNumber: Int, value: Boolean) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_VARINT)
        writeRawVarint(if (value) 1L else 0L)
    }

    /** Writes a tagged double field (fixed 64-bit). */
    fun writeDouble(fieldNumber: Int, value: Double) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_FIXED64)
        val bits = value.toRawBits()
        ensureCapacity(8)
        for (i in 0 until 8) {
            buffer[offset++] = ((bits ushr (i * 8)) and 0xFF).toByte()
        }
    }

    /** Writes a tagged float field (fixed 32-bit). */
    fun writeFloat(fieldNumber: Int, value: Float) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_FIXED32)
        val bits = value.toRawBits()
        ensureCapacity(4)
        for (i in 0 until 4) {
            buffer[offset++] = ((bits ushr (i * 8)) and 0xFF).toByte()
        }
    }

    /** Writes a tagged bytes field (length-delimited). */
    fun writeBytes(fieldNumber: Int, value: ByteArray) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
        writeRawVarint(value.size.toLong())
        writeRawBytes(value)
    }

    /** Writes a tagged embedded message field (length-delimited). */
    fun writeEmbedded(fieldNumber: Int, embeddedBytes: ByteArray) {
        writeTag(fieldNumber, WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
        writeRawVarint(embeddedBytes.size.toLong())
        writeRawBytes(embeddedBytes)
    }

    /**
     * Writes a field tag (field number + wire type) as a varint.
     */
    fun writeTag(fieldNumber: Int, wireType: Int) {
        writeRawVarint(WireFormat.makeTag(fieldNumber, wireType).toLong())
    }

    /** Writes a raw varint to the buffer. */
    fun writeRawVarint(value: Long) {
        val encoded = Varint.encode(value)
        writeRawBytes(encoded)
    }

    /** Writes raw bytes to the buffer. */
    fun writeRawBytes(bytes: ByteArray) {
        ensureCapacity(bytes.size)
        bytes.copyInto(buffer, offset)
        offset += bytes.size
    }

    /** Returns the accumulated buffer as a ByteArray. */
    fun toByteArray(): ByteArray = buffer.copyOfRange(0, offset)

    /** Returns the current buffer size in bytes. */
    val size: Int get() = offset

    /** Resets the writer for reuse. */
    fun reset() {
        offset = 0
    }
}
