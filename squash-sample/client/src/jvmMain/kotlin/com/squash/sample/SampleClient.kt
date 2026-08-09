package com.squash.sample

import com.squash.core.engine.SquashEngine
import com.squash.core.model.SquashEnvelope
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.Request
import com.squash.core.v2.engine.BinarySquashEngine

/**
 * Sample Kotlin/JVM SQUASH client that tests the protocol against the sample backend.
 *
 * Demonstrates:
 * - Sending SQUASH headers
 * - Receiving and decoding SQUASH envelopes
 * - Dictionary caching across requests
 *
 * Run the backend first:
 *     cd squash-sample/backend && uvicorn main:app --port 8000
 *
 * Then run this:
 *     ./gradlew :squash-sample:client:jvmRun
 */
fun main() {
    val baseUrl = "http://localhost:8000"
    val engine = SquashEngine()
    val binaryEngine = BinarySquashEngine()
    val json = Json { ignoreUnknownKeys = true }
    val client = OkHttpClient()

    println("\n${"=".repeat(60)}")
    println("  🔬 SQUASH Kotlin Client — E2E Test")
    println("=".repeat(60))

    // ─── Test 1: Non-SQUASH request ──────────────────────────
    println("\n── Test 1: Non-SQUASH Request ──")
    val request1 = Request.Builder().url("$baseUrl/users/1").build()
    val response1 = client.newCall(request1).execute()
    val body1 = response1.body?.string() ?: ""
    val data1 = json.parseToJsonElement(body1).jsonObject

    check("__meta" !in data1) { "Non-SQUASH should not have __meta" }
    check(data1["name"]?.jsonPrimitive?.content == "Ashwin Kumar")
    println("  ✅ Non-SQUASH client receives standard JSON")

    // ─── Test 2: First SQUASH request ────────────────────────
    println("\n── Test 2: First SQUASH Request ──")
    val request2 = Request.Builder()
        .url("$baseUrl/users/1")
        .header("Accept-Encoding", "squash")
        .build()
    val response2 = client.newCall(request2).execute()
    val body2 = response2.body?.string() ?: ""
    val envelope2 = json.decodeFromString<SquashEnvelope>(body2)

    check(envelope2.meta.version == 1)
    check(envelope2.dict != null) { "First request must include __dict" }

    val decoded2 = engine.decode(envelope2)
    check(decoded2.jsonObject["name"]?.jsonPrimitive?.content == "Ashwin Kumar")
    println("  ✅ First SQUASH request returns envelope with dict")
    println("  Dict ID: ${envelope2.meta.dictId}")
    println("  Dict keys: ${envelope2.dict?.size}")

    // ─── Test 3: Cached dict request ───────────────────────
    println("\n── Test 3: Cached Dict Request ──")
    val dictId = engine.dictStore.getDictId("api") ?: envelope2.meta.dictId
    val request3 = Request.Builder()
        .url("$baseUrl/users/1")
        .header("Accept-Encoding", "squash")
        .header("X-SQUASH-DictId", dictId)
        .build()
    val response3 = client.newCall(request3).execute()
    val body3 = response3.body?.string() ?: ""
    val envelope3 = json.decodeFromString<SquashEnvelope>(body3)

    check(envelope3.dict == null) { "Dict should be omitted when client is current" }

    val decoded3 = engine.decode(envelope3)
    check(decoded3.jsonObject["name"]?.jsonPrimitive?.content == "Ashwin Kumar")
    println("  ✅ Cached dict request omits __dict")

    // ─── Test 4: First SQUASH v2 Binary request ────────────────
    println("\n── Test 4: First SQUASH v2 Binary Request ──")
    val request4 = Request.Builder()
        .url("$baseUrl/users/1")
        .header("Accept", "application/squash+proto")
        .build()
    val response4 = client.newCall(request4).execute()
    val bodyBytes4 = response4.body?.bytes() ?: byteArrayOf()
    
    val decoded4 = binaryEngine.fromBinaryFrame(bodyBytes4)
    check(decoded4.data.jsonObject["name"]?.jsonPrimitive?.content == "Ashwin Kumar")
    println("  ✅ First SQUASH v2 request decodes successfully")
    println("  Dict ID: ${decoded4.dictId}")
    val v2DictId = decoded4.dictId

    // ─── Test 5: Cached SQUASH v2 Binary request ───────────────
    println("\n── Test 5: Cached SQUASH v2 Binary Request ──")
    val request5 = Request.Builder()
        .url("$baseUrl/users/1")
        .header("Accept", "application/squash+proto")
        .header("X-SQUASH-DictId", v2DictId)
        .build()
    val response5 = client.newCall(request5).execute()
    val bodyBytes5 = response5.body?.bytes() ?: byteArrayOf()
    
    val decoded5 = binaryEngine.fromBinaryFrame(bodyBytes5)
    check(decoded5.data.jsonObject["name"]?.jsonPrimitive?.content == "Ashwin Kumar")
    
    // We can also verify it's much smaller than the first request.
    println("  ✅ Cached SQUASH v2 request decodes successfully")
    println("  First request size: ${bodyBytes4.size} bytes")
    println("  Cached request size: ${bodyBytes5.size} bytes")
    check(bodyBytes5.size < bodyBytes4.size) { "Cached request should be smaller" }

    // ─── Summary ───────────────────────────────────────────
    println("\n${"=".repeat(60)}")
    println("  All tests passed! ✅")
    println("${"=".repeat(60)}\n")

    client.dispatcher.executorService.shutdown()
}
