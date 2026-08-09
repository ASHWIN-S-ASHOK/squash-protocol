package com.squash.core.v2

import com.squash.core.dict.DictionaryBuilder
import com.squash.core.v2.engine.VarintKeyMapper
import com.squash.core.v2.model.FieldType
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class VarintKeyMapperTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun convertsV1DictToV2() {
        val v1Dict = DictionaryBuilder.buildFromPaths("user", 1, listOf("name", "email", "age"))
        val v2Dict = VarintKeyMapper.fromV1Dictionary(v1Dict)

        assertEquals("user_v1", v2Dict.dictId)
        assertEquals(1, v2Dict.version)
        assertEquals(3, v2Dict.fieldCount)

        // Field tags should be 1-based
        assertEquals("name", v2Dict.fieldMappings[1])
        assertEquals("email", v2Dict.fieldMappings[2])
        assertEquals("age", v2Dict.fieldMappings[3])
    }

    @Test
    fun reverseMapping() {
        val v2Dict = VarintKeyMapper.buildDictionary("test", 1, listOf("a", "b", "c"))
        assertEquals(1, v2Dict.reverseMappings["a"])
        assertEquals(2, v2Dict.reverseMappings["b"])
        assertEquals(3, v2Dict.reverseMappings["c"])
    }

    @Test
    fun typeInferenceFromJson() {
        val sampleJson = json.parseToJsonElement("""
            {"name":"Ashwin","age":28,"active":true,"score":99.5}
        """.trimIndent())

        val v2Dict = VarintKeyMapper.buildDictionary(
            "user", 1,
            listOf("name", "age", "active", "score"),
            sampleJson,
        )

        assertEquals(FieldType.STRING, v2Dict.typeHints[1])   // name
        assertEquals(FieldType.INT64, v2Dict.typeHints[2])    // age
        assertEquals(FieldType.BOOL, v2Dict.typeHints[3])     // active
        assertEquals(FieldType.DOUBLE, v2Dict.typeHints[4])   // score
    }

    @Test
    fun nestedPathTypeInference() {
        val sampleJson = json.parseToJsonElement("""
            {"user":{"name":"Ashwin","address":{"city":"Mumbai"}}}
        """.trimIndent())

        val type = VarintKeyMapper.inferFieldType(sampleJson, "user.name")
        assertEquals(FieldType.STRING, type)

        val type2 = VarintKeyMapper.inferFieldType(sampleJson, "user.address.city")
        assertEquals(FieldType.STRING, type2)
    }

    @Test
    fun fifteenFieldsSingleByteRange() {
        // All 15 fields should have tags 1-15 (single-byte varint range)
        val paths = (1..15).map { "field$it" }
        val v2Dict = VarintKeyMapper.buildDictionary("wide", 1, paths)

        assertEquals(15, v2Dict.fieldCount)
        // All tags should be 1-15
        for (tag in 1..15) {
            assertTrue(tag in v2Dict.fieldMappings, "Tag $tag should exist")
        }
    }

    @Test
    fun schemaNameExtraction() {
        val v2Dict = VarintKeyMapper.buildDictionary("my_schema", 3, listOf("x"))
        assertEquals("my_schema", v2Dict.schemaName)
        assertEquals("my_schema_v3", v2Dict.dictId)
    }
}
