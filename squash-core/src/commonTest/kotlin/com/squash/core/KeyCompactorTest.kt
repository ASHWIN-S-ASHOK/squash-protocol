package com.squash.core

import com.squash.core.codec.KeyCompactor
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class KeyCompactorTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun flatObjectExtractsTopLevelKeys() {
        val element = json.parseToJsonElement("""{"name":"Ashwin","email":"a@b.com"}""")
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(listOf("name", "email"), paths)
    }

    @Test
    fun nestedObjectProducesDotNotation() {
        val element = json.parseToJsonElement("""
            {"user":{"name":"Ashwin","address":{"city":"Mumbai","zip":"400001"}}}
        """.trimIndent())
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(
            listOf("user.name", "user.address.city", "user.address.zip"),
            paths,
        )
    }

    @Test
    fun arrayOfObjectsUsesFirstElementForKeys() {
        val element = json.parseToJsonElement("""
            {"users":[{"name":"Ashwin","age":28},{"name":"Ravi","age":30}]}
        """.trimIndent())
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(listOf("users.name", "users.age"), paths)
    }

    @Test
    fun arrayOfPrimitivesIsTreatedAsLeaf() {
        val element = json.parseToJsonElement("""{"tags":["kotlin","java"],"name":"lib"}""")
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(listOf("tags", "name"), paths)
    }

    @Test
    fun buildMappingAssignsBase62Keys() {
        val paths = listOf("name", "email", "address.city")
        val mapping = KeyCompactor.buildMapping(paths)
        assertEquals(
            mapOf("a" to "name", "b" to "email", "c" to "address.city"),
            mapping,
        )
    }

    @Test
    fun emptyObjectProducesNoPaths() {
        val element = json.parseToJsonElement("{}")
        val paths = KeyCompactor.extractKeyPaths(element)
        assertTrue(paths.isEmpty())
    }

    @Test
    fun deeplyNestedObjectFlattensCorrectly() {
        val element = json.parseToJsonElement("""
            {"a":{"b":{"c":{"d":"value"}}}}
        """.trimIndent())
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(listOf("a.b.c.d"), paths)
    }

    @Test
    fun noDuplicatePaths() {
        // Even if structurally identical keys appear, paths should be unique
        val element = json.parseToJsonElement("""
            {"x":"1","y":"2","z":"3"}
        """.trimIndent())
        val paths = KeyCompactor.extractKeyPaths(element)
        assertEquals(paths.size, paths.toSet().size)
    }
}
