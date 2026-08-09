package com.squash.core

import com.squash.core.codec.JsonTransformer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals

class JsonTransformerTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun compactFlatObject() {
        val original = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")
        val reverseMapping = mapOf("name" to "a", "email" to "b")

        val compacted = JsonTransformer.compact(original, reverseMapping)
        val obj = compacted.jsonObject

        assertEquals(JsonPrimitive("Ashwin"), obj["a"])
        assertEquals(JsonPrimitive("a@b.com"), obj["b"])
    }

    @Test
    fun compactNestedObject() {
        val original = json.parseToJsonElement("""
            {"user":{"name":"Ashwin","address":{"city":"Mumbai"}}}
        """.trimIndent())
        val reverseMapping = mapOf(
            "user.name" to "a",
            "user.address.city" to "b",
        )

        val compacted = JsonTransformer.compact(original, reverseMapping)
        val obj = compacted.jsonObject

        assertEquals(JsonPrimitive("Ashwin"), obj["a"])
        assertEquals(JsonPrimitive("Mumbai"), obj["b"])
    }

    @Test
    fun expandFlatObject() {
        val compacted = json.parseToJsonElement("""{"a":"Ashwin","b":"a@b.com"}""")
        val mapping = mapOf("a" to "name", "b" to "email")

        val expanded = JsonTransformer.expand(compacted, mapping)
        val obj = expanded.jsonObject

        assertEquals(JsonPrimitive("Ashwin"), obj["name"])
        assertEquals(JsonPrimitive("a@b.com"), obj["email"])
    }

    @Test
    fun expandToNestedObject() {
        val compacted = json.parseToJsonElement("""{"a":"Ashwin","b":"Mumbai"}""")
        val mapping = mapOf(
            "a" to "user.name",
            "b" to "user.address.city",
        )

        val expanded = JsonTransformer.expand(compacted, mapping)
        val user = expanded.jsonObject["user"]!!.jsonObject

        assertEquals(JsonPrimitive("Ashwin"), user["name"])
        assertEquals(JsonPrimitive("Mumbai"), user["address"]!!.jsonObject["city"])
    }

    @Test
    fun roundTripPreservesData() {
        val original = json.parseToJsonElement("""
            {"user":{"name":"Ashwin","email":"a@b.com","address":{"city":"Mumbai","zip":"400001"}}}
        """.trimIndent())

        val reverseMapping = mapOf(
            "user.name" to "a",
            "user.email" to "b",
            "user.address.city" to "c",
            "user.address.zip" to "d",
        )
        val mapping = reverseMapping.entries.associate { (k, v) -> v to k }

        val compacted = JsonTransformer.compact(original, reverseMapping)
        val expanded = JsonTransformer.expand(compacted, mapping)

        assertEquals(
            original.jsonObject["user"]!!.jsonObject["name"]!!.jsonPrimitive.content,
            expanded.jsonObject["user"]!!.jsonObject["name"]!!.jsonPrimitive.content,
        )
        assertEquals(
            original.jsonObject["user"]!!.jsonObject["address"]!!.jsonObject["city"]!!.jsonPrimitive.content,
            expanded.jsonObject["user"]!!.jsonObject["address"]!!.jsonObject["city"]!!.jsonPrimitive.content,
        )
    }

    @Test
    fun compactPreservesPrimitives() {
        val original = json.parseToJsonElement("""{"count":42,"active":true,"name":"test"}""")
        val reverseMapping = mapOf("count" to "a", "active" to "b", "name" to "c")

        val compacted = JsonTransformer.compact(original, reverseMapping)
        val obj = compacted.jsonObject

        assertEquals(JsonPrimitive(42), obj["a"])
        assertEquals(JsonPrimitive(true), obj["b"])
        assertEquals(JsonPrimitive("test"), obj["c"])
    }

    @Test
    fun expandWithUnknownKeysPassesThrough() {
        val compacted = json.parseToJsonElement("""{"a":"value","unknown":"other"}""")
        val mapping = mapOf("a" to "name")

        val expanded = JsonTransformer.expand(compacted, mapping)
        val obj = expanded.jsonObject

        assertEquals(JsonPrimitive("value"), obj["name"])
        assertEquals(JsonPrimitive("other"), obj["unknown"])
    }
}
