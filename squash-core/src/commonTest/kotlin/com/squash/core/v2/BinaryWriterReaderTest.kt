package com.squash.core.v2

import com.squash.core.v2.wire.BinaryReader
import com.squash.core.v2.wire.BinaryWriter
import com.squash.core.v2.wire.WireFormat
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class BinaryWriterReaderTest {

    @Test
    fun stringRoundTrip() {
        val writer = BinaryWriter()
        writer.writeString(1, "Hello, SQUASH!")
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        val tag = reader.readTag()
        assertEquals(1, WireFormat.fieldNumber(tag))
        assertEquals(WireFormat.WIRE_TYPE_LENGTH_DELIMITED, WireFormat.wireType(tag))
        assertEquals("Hello, SQUASH!", reader.readString())
        assertTrue(reader.isAtEnd())
    }

    @Test
    fun intRoundTrip() {
        val writer = BinaryWriter()
        writer.writeInt64(2, 42)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        val tag = reader.readTag()
        assertEquals(2, WireFormat.fieldNumber(tag))
        assertEquals(WireFormat.WIRE_TYPE_VARINT, WireFormat.wireType(tag))
        assertEquals(42L, reader.readVarint())
        assertTrue(reader.isAtEnd())
    }

    @Test
    fun boolRoundTrip() {
        val writer = BinaryWriter()
        writer.writeBool(3, true)
        writer.writeBool(4, false)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)

        val tag1 = reader.readTag()
        assertEquals(3, WireFormat.fieldNumber(tag1))
        assertTrue(reader.readBool())

        val tag2 = reader.readTag()
        assertEquals(4, WireFormat.fieldNumber(tag2))
        assertEquals(false, reader.readBool())
        assertTrue(reader.isAtEnd())
    }

    @Test
    fun doubleRoundTrip() {
        val writer = BinaryWriter()
        writer.writeDouble(5, 3.14159265)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        val tag = reader.readTag()
        assertEquals(5, WireFormat.fieldNumber(tag))
        assertEquals(WireFormat.WIRE_TYPE_FIXED64, WireFormat.wireType(tag))
        assertEquals(3.14159265, reader.readDouble())
        assertTrue(reader.isAtEnd())
    }

    @Test
    fun bytesRoundTrip() {
        val writer = BinaryWriter()
        val data = byteArrayOf(0x01, 0x02, 0x03, 0x04)
        writer.writeBytes(6, data)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        val tag = reader.readTag()
        assertEquals(6, WireFormat.fieldNumber(tag))
        assertEquals(data.toList(), reader.readBytes().toList())
        assertTrue(reader.isAtEnd())
    }

    @Test
    fun multipleFieldsRoundTrip() {
        val writer = BinaryWriter()
        writer.writeString(1, "Ashwin")
        writer.writeString(2, "ashwin@email.com")
        writer.writeInt64(3, 28)
        writer.writeBool(4, true)
        writer.writeDouble(5, 99.99)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)

        assertEquals(1, WireFormat.fieldNumber(reader.readTag()))
        assertEquals("Ashwin", reader.readString())

        assertEquals(2, WireFormat.fieldNumber(reader.readTag()))
        assertEquals("ashwin@email.com", reader.readString())

        assertEquals(3, WireFormat.fieldNumber(reader.readTag()))
        assertEquals(28L, reader.readVarint())

        assertEquals(4, WireFormat.fieldNumber(reader.readTag()))
        assertTrue(reader.readBool())

        assertEquals(5, WireFormat.fieldNumber(reader.readTag()))
        assertEquals(99.99, reader.readDouble())

        assertTrue(reader.isAtEnd())
    }

    @Test
    fun skipUnknownFields() {
        val writer = BinaryWriter()
        writer.writeString(1, "known")
        writer.writeInt64(99, 12345) // Unknown field
        writer.writeString(2, "also known")
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)

        val tag1 = reader.readTag()
        assertEquals(1, WireFormat.fieldNumber(tag1))
        assertEquals("known", reader.readString())

        val tag2 = reader.readTag()
        assertEquals(99, WireFormat.fieldNumber(tag2))
        reader.skipField(WireFormat.wireType(tag2)) // Skip unknown

        val tag3 = reader.readTag()
        assertEquals(2, WireFormat.fieldNumber(tag3))
        assertEquals("also known", reader.readString())

        assertTrue(reader.isAtEnd())
    }

    @Test
    fun emptyStringField() {
        val writer = BinaryWriter()
        writer.writeString(1, "")
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        reader.readTag()
        assertEquals("", reader.readString())
    }

    @Test
    fun largeString() {
        val longStr = "x".repeat(1000)
        val writer = BinaryWriter()
        writer.writeString(1, longStr)
        val bytes = writer.toByteArray()

        val reader = BinaryReader(bytes)
        reader.readTag()
        assertEquals(longStr, reader.readString())
    }

    @Test
    fun resetWriter() {
        val writer = BinaryWriter()
        writer.writeString(1, "test")
        assertTrue(writer.size > 0)
        writer.reset()
        assertEquals(0, writer.size)
    }
}
