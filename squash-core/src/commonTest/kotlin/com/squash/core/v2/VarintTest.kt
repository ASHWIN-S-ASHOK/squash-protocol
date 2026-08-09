package com.squash.core.v2

import com.squash.core.v2.wire.Varint
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class VarintTest {

    @Test
    fun encodeSingleByte() {
        // Values 0-127 should encode as a single byte
        assertEquals(byteArrayOf(0).toList(), Varint.encode(0).toList())
        assertEquals(byteArrayOf(1).toList(), Varint.encode(1).toList())
        assertEquals(byteArrayOf(127).toList(), Varint.encode(127).toList())
    }

    @Test
    fun encodeTwoBytes() {
        // 128 = 0x80 → [0x80, 0x01]
        val encoded = Varint.encode(128)
        assertEquals(2, encoded.size)
        assertEquals(listOf(0x80.toByte(), 0x01.toByte()), encoded.toList())
    }

    @Test
    fun encode300() {
        // 300 = 0x012C → [0xAC, 0x02]
        val encoded = Varint.encode(300)
        assertEquals(2, encoded.size)
        assertEquals(listOf(0xAC.toByte(), 0x02.toByte()), encoded.toList())
    }

    @Test
    fun encodeLargeValue() {
        // 16384 should need 3 bytes
        val encoded = Varint.encode(16384)
        assertEquals(3, encoded.size)
    }

    @Test
    fun decodeRoundTrip() {
        val testValues = listOf(0L, 1L, 127L, 128L, 255L, 300L, 16383L, 16384L, 2097151L, Int.MAX_VALUE.toLong())
        for (value in testValues) {
            val encoded = Varint.encode(value)
            val result = Varint.decode(encoded)
            assertEquals(value, result.value, "Round-trip failed for value $value")
            assertEquals(encoded.size, result.bytesRead, "bytesRead mismatch for value $value")
        }
    }

    @Test
    fun decodeFromOffset() {
        val prefix = byteArrayOf(0xFF.toByte(), 0xFF.toByte())
        val varint = Varint.encode(42)
        val combined = prefix + varint

        val result = Varint.decode(combined, offset = 2)
        assertEquals(42L, result.value)
        assertEquals(1, result.bytesRead)
    }

    @Test
    fun fieldTagsOneToFifteenAreSingleByte() {
        // Critical for SQUASH v2: field tags 1-15 with any wire type
        // should produce single-byte varints for the tag
        for (fieldNumber in 1..15) {
            for (wireType in listOf(0, 1, 2, 5)) {
                val tag = (fieldNumber shl 3) or wireType
                val encoded = Varint.encode(tag)
                assertEquals(
                    1, encoded.size,
                    "Field $fieldNumber with wire type $wireType should be single-byte, got ${encoded.size}",
                )
            }
        }
    }

    @Test
    fun fieldTag16RequiresTwoBytes() {
        // Field 16 with wire type 2: tag = (16 << 3) | 2 = 130
        val tag = (16 shl 3) or 2
        val encoded = Varint.encode(tag)
        assertEquals(2, encoded.size, "Field 16 tag should be 2 bytes")
    }

    @Test
    fun intOverload() {
        val encoded = Varint.encode(42)
        val decoded = Varint.decode(encoded)
        assertEquals(42, decoded.intValue)
    }
}
