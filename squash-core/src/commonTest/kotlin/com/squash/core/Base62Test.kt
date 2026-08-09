package com.squash.core

import com.squash.core.codec.Base62
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class Base62Test {

    @Test
    fun singleCharLowercaseRange() {
        assertEquals("a", Base62.encode(0))
        assertEquals("b", Base62.encode(1))
        assertEquals("z", Base62.encode(25))
    }

    @Test
    fun singleCharUppercaseRange() {
        assertEquals("A", Base62.encode(26))
        assertEquals("B", Base62.encode(27))
        assertEquals("Z", Base62.encode(51))
    }

    @Test
    fun singleCharDigitRange() {
        assertEquals("0", Base62.encode(52))
        assertEquals("1", Base62.encode(53))
        assertEquals("9", Base62.encode(61))
    }

    @Test
    fun multiCharKeysStartAtIndex62() {
        assertEquals("aa", Base62.encode(62))
        assertEquals("ab", Base62.encode(63))
        assertEquals("az", Base62.encode(87))
        assertEquals("aA", Base62.encode(88))
        assertEquals("a9", Base62.encode(123))
    }

    @Test
    fun multiCharSecondGroup() {
        // Index 124 should be "ba" (second character group)
        assertEquals("ba", Base62.encode(124))
        assertEquals("bb", Base62.encode(125))
    }

    @Test
    fun generateKeysProducesCorrectCount() {
        val keys = Base62.generateKeys(5)
        assertEquals(listOf("a", "b", "c", "d", "e"), keys)
    }

    @Test
    fun generateKeysAcrossBoundary() {
        val keys = Base62.generateKeys(64)
        assertEquals("a", keys.first())
        assertEquals("9", keys[61])
        assertEquals("aa", keys[62])
        assertEquals("ab", keys[63])
    }

    @Test
    fun generateKeysEmpty() {
        assertEquals(emptyList(), Base62.generateKeys(0))
    }

    @Test
    fun negativeIndexThrows() {
        assertFailsWith<IllegalArgumentException> {
            Base62.encode(-1)
        }
    }

    @Test
    fun negativeCountThrows() {
        assertFailsWith<IllegalArgumentException> {
            Base62.generateKeys(-1)
        }
    }

    @Test
    fun allSingleCharKeysAreUnique() {
        val keys = Base62.generateKeys(62)
        assertEquals(62, keys.toSet().size)
    }

    @Test
    fun first200KeysAreUnique() {
        val keys = Base62.generateKeys(200)
        assertEquals(200, keys.toSet().size)
    }
}
