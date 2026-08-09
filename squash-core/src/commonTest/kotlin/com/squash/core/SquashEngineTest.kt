package com.squash.core

import com.squash.core.dict.DictionaryBuilder
import com.squash.core.engine.SquashEngine
import com.squash.core.model.SquashDictionary
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SquashEngineTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun encodeCreatesValidEnvelope() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        val envelope = engine.encode(original, "user")

        assertEquals(1, envelope.meta.version)
        assertEquals("user_v1", envelope.meta.dictId)
        assertEquals("map", envelope.meta.encoding)
        assertNotNull(envelope.dict, "First encode should include __dict")
        assertNotNull(envelope.data)
    }

    @Test
    fun encodeOmitsDictWhenClientIsCurrent() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        // First call — builds and caches the dict
        engine.encode(original, "user")

        // Second call — client already has the dict
        val envelope = engine.encode(original, "user", clientDictId = "user_v1")

        assertNull(envelope.dict, "Dict should be omitted when client is current")
    }

    @Test
    fun encodeIncludesDictOnVersionMismatch() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        engine.encode(original, "user")

        // Client has stale version
        val envelope = engine.encode(original, "user", clientDictId = "user_v0")

        assertNotNull(envelope.dict, "Dict should be included on version mismatch")
    }

    @Test
    fun decodeWithEmbeddedDict() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        val envelope = engine.encode(original, "user")
        val decoded = engine.decode(envelope)

        assertEquals(
            "Ashwin",
            decoded.jsonObject["name"]?.jsonPrimitive?.content,
        )
        assertEquals(
            "a@b.com",
            decoded.jsonObject["email"]?.jsonPrimitive?.content,
        )
    }

    @Test
    fun decodeWithCachedDict() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")

        // First encode caches the dict
        val envelope1 = engine.encode(original, "user")
        engine.decode(envelope1) // This caches the dict from envelope

        // Second encode without dict (client is current)
        val envelope2 = engine.encode(original, "user", clientDictId = "user_v1")
        assertNull(envelope2.dict)

        // Should still decode using cached dict
        val decoded = engine.decode(envelope2)
        assertEquals("Ashwin", decoded.jsonObject["name"]?.jsonPrimitive?.content)
    }

    @Test
    fun decodeWithoutDictOrCacheThrows() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Ashwin"}""")

        // Encode with one engine, decode with a fresh one that has no cache
        val engine1 = SquashEngine()
        val envelope = engine1.encode(original, "user", clientDictId = "user_v1")
        // This envelope has no __dict and fresh engine2 has no cache

        val engine2 = SquashEngine()
        assertFailsWith<IllegalStateException> {
            engine2.decode(envelope)
        }
    }

    @Test
    fun fullRoundTrip() {
        val engine = SquashEngine()
        val originalString = """{"user":{"name":"Ashwin","address":{"city":"Mumbai","zip":"400001"}}}"""
        val original = json.parseToJsonElement(originalString)

        val envelope = engine.encode(original, "profile")
        val decoded = engine.decode(envelope)

        val user = decoded.jsonObject["user"]!!.jsonObject
        assertEquals("Ashwin", user["name"]!!.jsonPrimitive.content)
        assertEquals("Mumbai", user["address"]!!.jsonObject["city"]!!.jsonPrimitive.content)
        assertEquals("400001", user["address"]!!.jsonObject["zip"]!!.jsonPrimitive.content)
    }

    @Test
    fun encodeDecodeViaStrings() {
        val engine = SquashEngine()
        val original = json.parseToJsonElement("""{"name":"Test","value":42}""")

        val envelope = engine.encode(original, "simple")
        val envelopeString = engine.envelopeToString(envelope)

        // Decode from string (simulates receiving over the wire)
        val decoded = engine.decodeFromString(envelopeString)

        assertEquals("Test", decoded.jsonObject["name"]!!.jsonPrimitive.content)
        assertEquals("42", decoded.jsonObject["value"]!!.jsonPrimitive.content)
    }

    @Test
    fun shouldIncludeDictLogic() {
        val engine = SquashEngine()

        assertTrue(engine.shouldIncludeDict("user_v1", null))
        assertTrue(engine.shouldIncludeDict("user_v2", "user_v1"))
        assertEquals(false, engine.shouldIncludeDict("user_v1", "user_v1"))
    }

    @Test
    fun registerDictionaryManually() {
        val engine = SquashEngine()
        val dict = DictionaryBuilder.buildFromPaths("custom", 1, listOf("field1", "field2"))

        engine.registerDictionary(dict)

        assertNotNull(engine.dictStore.get("custom"))
        assertEquals("custom_v1", engine.dictStore.getDictId("custom"))
    }
}
