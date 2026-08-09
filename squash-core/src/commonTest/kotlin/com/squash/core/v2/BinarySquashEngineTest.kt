package com.squash.core.v2

import com.squash.core.v2.engine.BinarySquashEngine
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class BinarySquashEngineTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun encodeDecodeFlatPayload() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        val frame = engine.toBinaryFrame(original, "user")
        val result = engine.fromBinaryFrame(frame)

        assertEquals("Ashwin", result.data.jsonObject["name"]?.jsonPrimitive?.content)
        assertEquals("a@b.com", result.data.jsonObject["email"]?.jsonPrimitive?.content)
        assertEquals(2, result.version)
        assertEquals("user_v1", result.dictId)
    }

    @Test
    fun encodeDecodeNestedPayload() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""
            {"user":{"name":"Ashwin","address":{"city":"Mumbai","zip":"400001"}}}
        """.trimIndent())

        val frame = engine.toBinaryFrame(original, "profile")
        val result = engine.fromBinaryFrame(frame)

        val user = result.data.jsonObject["user"]!!.jsonObject
        assertEquals("Ashwin", user["name"]?.jsonPrimitive?.content)
        assertEquals("Mumbai", user["address"]?.jsonObject?.get("city")?.jsonPrimitive?.content)
        assertEquals("400001", user["address"]?.jsonObject?.get("zip")?.jsonPrimitive?.content)
    }

    @Test
    fun encodeDecodeWithMixedTypes() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""
            {"name":"Ashwin","age":28,"active":true,"score":99.5}
        """.trimIndent())

        val frame = engine.toBinaryFrame(original, "typed")
        val result = engine.fromBinaryFrame(frame)

        val data = result.data.jsonObject
        assertEquals("Ashwin", data["name"]?.jsonPrimitive?.content)
        assertEquals("28", data["age"]?.jsonPrimitive?.content)
        assertEquals("true", data["active"]?.jsonPrimitive?.content)
        assertEquals("99.5", data["score"]?.jsonPrimitive?.content)
    }

    @Test
    fun dictOmittedWhenClientIsCurrent() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin"}""")

        // First encode — dict included
        val frame1 = engine.toBinaryFrame(original, "user")
        assertTrue(frame1.isNotEmpty())

        // Second encode with matching dictId — dict should be smaller
        val frame2 = engine.toBinaryFrame(original, "user", clientDictId = "user_v1")
        assertTrue(frame2.size < frame1.size, "Frame without dict should be smaller")

        // Should still decode correctly
        val result = engine.fromBinaryFrame(frame2)
        assertEquals("Ashwin", result.data.jsonObject["name"]?.jsonPrimitive?.content)
    }

    @Test
    fun decodeWithoutDictOrCacheThrows() {
        val engine1 = BinarySquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin"}""")

        // Encode with dict omitted
        val frame = engine1.toBinaryFrame(original, "user", clientDictId = "user_v1")

        // Fresh engine with no cache
        val engine2 = BinarySquashEngine()
        assertFailsWith<IllegalStateException> {
            engine2.fromBinaryFrame(frame)
        }
    }

    @Test
    fun binarySizeMuchSmallerThanJson() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""
            {
                "user": {
                    "name": "Ashwin Kumar",
                    "email": "ashwin@email.com",
                    "age": 28,
                    "is_active": true,
                    "address": {
                        "street": "123 MG Road",
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "zip_code": "400001",
                        "country": "India"
                    }
                }
            }
        """.trimIndent())

        val jsonSize = json.encodeToString(
            kotlinx.serialization.json.JsonElement.serializer(),
            original,
        ).length

        // Binary with dict (first request)
        val frameWithDict = engine.toBinaryFrame(original, "user_profile")

        // Binary without dict (subsequent request)
        val frameNoDict = engine.toBinaryFrame(original, "user_profile", clientDictId = "user_profile_v1")

        println("  JSON size:             $jsonSize bytes")
        println("  Binary (with dict):    ${frameWithDict.size} bytes (${100 * frameWithDict.size / jsonSize}%)")
        println("  Binary (no dict):      ${frameNoDict.size} bytes (${100 * frameNoDict.size / jsonSize}%)")

        // Binary without dict should be significantly smaller than JSON
        assertTrue(
            frameNoDict.size < jsonSize,
            "Binary (no dict) should be smaller than JSON: ${frameNoDict.size} vs $jsonSize",
        )
    }

    @Test
    fun payloadEncodeDecodeIsolated() {
        val engine = BinarySquashEngine()
        val original = json.parseToJsonElement("""{"x":"hello","y":"world"}""")

        val keyPaths = listOf("x", "y")
        val dict = com.squash.core.v2.engine.VarintKeyMapper.buildDictionary("t", 1, keyPaths, original)

        val payloadBytes = engine.encodePayload(original, dict)
        val decoded = engine.decodePayload(payloadBytes, dict)

        assertEquals("hello", decoded.jsonObject["x"]?.jsonPrimitive?.content)
        assertEquals("world", decoded.jsonObject["y"]?.jsonPrimitive?.content)
    }
}
