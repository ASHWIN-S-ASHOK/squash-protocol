package com.squash.core.v2.engine

import com.squash.core.codec.KeyCompactor
import com.squash.core.v2.model.BinaryDictionary
import com.squash.core.v2.model.EncodingType
import com.squash.core.v2.model.FieldType
import com.squash.core.v2.wire.BinaryReader
import com.squash.core.v2.wire.BinaryWriter
import com.squash.core.v2.wire.WireFormat
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.longOrNull

/**
 * SQUASH v2 Binary Protocol Engine.
 *
 * Encodes JSON payloads into compact binary frames using Protobuf wire format
 * with Varint-indexed field tags, and decodes them back.
 *
 * ## Binary Frame Structure
 *
 * A complete binary frame consists of:
 * ```
 * [Meta fields (tag 1-3)] [Dict fields (tag 4, optional)] [Payload (tag 5)]
 * ```
 *
 * The frame itself is a sequence of Protobuf-style tagged fields:
 * - Tag 1 (varint): protocol version
 * - Tag 2 (string): dictId
 * - Tag 3 (varint): encoding type
 * - Tag 4 (bytes): serialized dictionary (only if client needs sync)
 * - Tag 5 (bytes): binary-encoded payload
 *
 * ## Payload Encoding (BINARY_MAP mode)
 *
 * Each leaf value from the flattened JSON is written as a Protobuf field:
 * ```
 * [varint_tag] [value]
 * ```
 * Where `varint_tag = (field_number << 3) | wire_type`.
 *
 * Fields 1–15 use single-byte tags, making common fields extremely compact.
 */
class BinarySquashEngine(
    private val dictStore: MutableMap<String, BinaryDictionary> = mutableMapOf(),
    val json: Json = Json { ignoreUnknownKeys = true },
) {

    // Frame-level field numbers
    companion object {
        const val FRAME_VERSION = 1
        const val FRAME_DICT_ID = 2
        const val FRAME_ENCODING = 3
        const val FRAME_DICT_DATA = 4
        const val FRAME_PAYLOAD = 5
    }

    /**
     * Encodes a JSON payload into a compact binary frame.
     *
     * @param originalJson The original JSON payload.
     * @param schemaName   Schema name for dictionary lookup/creation.
     * @param clientDictId Client's cached dictId for sync logic.
     * @return Binary frame as a [ByteArray].
     */
    fun toBinaryFrame(
        originalJson: JsonElement,
        schemaName: String,
        clientDictId: String? = null,
    ): ByteArray {
        // Get or build v2 dictionary
        val dictionary = dictStore[schemaName]
            ?: run {
                val keyPaths = KeyCompactor.extractKeyPaths(originalJson)
                VarintKeyMapper.buildDictionary(schemaName, 1, keyPaths, originalJson)
                    .also { dictStore[schemaName] = it }
            }

        // Encode the payload as binary
        val payloadBytes = encodePayload(originalJson, dictionary)

        // Determine if we need to include the dictionary
        val includeDict = shouldIncludeDict(dictionary.dictId, clientDictId)

        // Write the complete frame
        val frameWriter = BinaryWriter()

        // Meta fields
        frameWriter.writeInt64(FRAME_VERSION, 2)
        frameWriter.writeString(FRAME_DICT_ID, dictionary.dictId)
        frameWriter.writeInt64(FRAME_ENCODING, EncodingType.BINARY_MAP.value.toLong())

        // Dictionary (optional)
        if (includeDict) {
            val dictBytes = serializeDictionary(dictionary)
            frameWriter.writeBytes(FRAME_DICT_DATA, dictBytes)
        }

        // Payload
        frameWriter.writeBytes(FRAME_PAYLOAD, payloadBytes)

        return frameWriter.toByteArray()
    }

    /**
     * Decodes a binary frame back into the original JSON structure.
     *
     * @param frameBytes The binary frame bytes.
     * @return A [DecompactResult] containing the expanded JSON and metadata.
     */
    fun fromBinaryFrame(frameBytes: ByteArray): DecompactResult {
        val reader = BinaryReader(frameBytes)

        var version = 2
        var dictId = ""
        var encoding = EncodingType.BINARY_MAP
        var dictBytes: ByteArray? = null
        var payloadBytes: ByteArray? = null

        // Read frame fields
        while (!reader.isAtEnd()) {
            val tag = reader.readTag()
            if (tag == 0) break
            val fieldNumber = WireFormat.fieldNumber(tag)
            val wireType = WireFormat.wireType(tag)

            when (fieldNumber) {
                FRAME_VERSION -> version = reader.readVarint().toInt()
                FRAME_DICT_ID -> dictId = reader.readString()
                FRAME_ENCODING -> encoding = EncodingType.fromValue(reader.readVarint().toInt())
                FRAME_DICT_DATA -> dictBytes = reader.readBytes()
                FRAME_PAYLOAD -> payloadBytes = reader.readBytes()
                else -> reader.skipField(wireType)
            }
        }

        requireNotNull(payloadBytes) { "Binary frame has no payload (field 5)" }
        require(dictId.isNotEmpty()) { "Binary frame has no dictId (field 2)" }

        // Resolve dictionary
        val dictionary = if (dictBytes != null) {
            val dict = deserializeDictionary(dictBytes, dictId)
            dictStore[dict.schemaName] = dict
            dict
        } else {
            dictStore.values.find { it.dictId == dictId }
                ?: throw IllegalStateException(
                    "No dictionary found for dictId '$dictId'. " +
                        "The server should have included dict data in the frame."
                )
        }

        // Decode payload
        val expandedJson = decodePayload(payloadBytes, dictionary)

        return DecompactResult(
            data = expandedJson,
            dictId = dictId,
            version = version,
            encoding = encoding,
        )
    }

    /**
     * Encodes a JSON element as binary using the dictionary's field mappings.
     */
    fun encodePayload(json: JsonElement, dictionary: BinaryDictionary): ByteArray {
        val writer = BinaryWriter()
        val flatValues = flattenJson(json)

        for ((keyPath, value) in flatValues) {
            val fieldTag = dictionary.reverseMappings[keyPath] ?: continue
            val fieldType = dictionary.typeFor(fieldTag)

            writeFieldValue(writer, fieldTag, value, fieldType)
        }

        return writer.toByteArray()
    }

    /**
     * Decodes binary payload bytes into a nested JSON object.
     */
    fun decodePayload(payloadBytes: ByteArray, dictionary: BinaryDictionary): JsonElement {
        val reader = BinaryReader(payloadBytes)
        val values = mutableMapOf<String, JsonElement>()

        while (!reader.isAtEnd()) {
            val tag = reader.readTag()
            if (tag == 0) break
            val fieldNumber = WireFormat.fieldNumber(tag)
            val wireType = WireFormat.wireType(tag)

            val keyPath = dictionary.fieldMappings[fieldNumber]
            if (keyPath == null) {
                reader.skipField(wireType)
                continue
            }

            val fieldType = dictionary.typeFor(fieldNumber)
            val jsonValue = readFieldValue(reader, wireType, fieldType, dictionary)
            values[keyPath] = jsonValue
        }

        // Unflatten dot-notation paths into nested JSON
        return unflattenToJson(values)
    }

    // ─── Payload Field Encoding ──────────────────────────────

    private fun writeFieldValue(
        writer: BinaryWriter,
        fieldTag: Int,
        value: JsonElement,
        fieldType: FieldType,
    ) {
        when (value) {
            is JsonPrimitive -> {
                when {
                    value.isString -> {
                        val str = value.content
                        val index = dictionary.reverseValueDictionary[str]
                        if (index != null) {
                            writer.writeInt64(fieldTag, index.toLong()) // Dynamic wire type switch
                        } else {
                            writer.writeString(fieldTag, str)
                        }
                    }
                    value.booleanOrNull != null -> writer.writeBool(fieldTag, value.booleanOrNull!!)
                    value.longOrNull != null -> writer.writeInt64(fieldTag, value.longOrNull!!)
                    value.doubleOrNull != null -> writer.writeDouble(fieldTag, value.doubleOrNull!!)
                    else -> writer.writeString(fieldTag, value.content)
                }
            }
            is JsonNull -> { /* Skip null values */ }
            else -> {
                // Complex values (arrays, objects) — serialize as JSON string bytes
                val jsonStr = this.json.encodeToString(JsonElement.serializer(), value)
                writer.writeString(fieldTag, jsonStr)
            }
        }
    }

    private fun readFieldValue(
        reader: BinaryReader,
        wireType: Int,
        fieldType: FieldType,
        dictionary: BinaryDictionary,
    ): JsonElement {
        return when (wireType) {
            WireFormat.WIRE_TYPE_VARINT -> {
                val v = reader.readVarint()
                when (fieldType) {
                    FieldType.BOOL -> JsonPrimitive(v != 0L)
                    FieldType.STRING -> {
                        val str = dictionary.valueDictionary.getOrNull(v.toInt()) ?: ""
                        JsonPrimitive(str)
                    }
                    else -> JsonPrimitive(v)
                }
            }
            WireFormat.WIRE_TYPE_FIXED64 -> JsonPrimitive(reader.readDouble())
            WireFormat.WIRE_TYPE_FIXED32 -> JsonPrimitive(reader.readFloat())
            WireFormat.WIRE_TYPE_LENGTH_DELIMITED -> {
                val str = reader.readString()
                when (fieldType) {
                    FieldType.EMBEDDED -> parseJsonOrString(str)
                    FieldType.STRING -> {
                        val trimmed = str.trimStart()
                        if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
                            parseJsonOrString(str)
                        } else {
                            JsonPrimitive(str)
                        }
                    }
                    else -> JsonPrimitive(str)
                }
            }
            else -> {
                reader.skipField(wireType)
                JsonNull
            }
        }
    }

    private fun parseJsonOrString(str: String): JsonElement {
        return try {
            json.parseToJsonElement(str)
        } catch (_: Exception) {
            JsonPrimitive(str)
        }
    }

    // ─── JSON Flatten / Unflatten ────────────────────────────

    private fun flattenJson(
        element: JsonElement,
        prefix: String = "",
    ): Map<String, JsonElement> {
        val result = mutableMapOf<String, JsonElement>()
        when (element) {
            is JsonObject -> {
                for ((key, value) in element) {
                    val fullPath = if (prefix.isEmpty()) key else "$prefix.$key"
                    when (value) {
                        is JsonObject -> result.putAll(flattenJson(value, fullPath))
                        else -> result[fullPath] = value
                    }
                }
            }
            else -> {
                if (prefix.isNotEmpty()) result[prefix] = element
            }
        }
        return result
    }

    @Suppress("UNCHECKED_CAST")
    private fun unflattenToJson(flat: Map<String, JsonElement>): JsonElement {
        val nested = mutableMapOf<String, Any>()
        for ((path, value) in flat) {
            val parts = path.split(".")
            var current = nested
            for (i in 0 until parts.size - 1) {
                current = current.getOrPut(parts[i]) {
                    mutableMapOf<String, Any>()
                } as MutableMap<String, Any>
            }
            current[parts.last()] = value
        }
        return buildNestedJson(nested)
    }

    @Suppress("UNCHECKED_CAST")
    private fun buildNestedJson(map: Map<String, Any>): JsonElement {
        return buildJsonObject {
            for ((key, value) in map) {
                when (value) {
                    is Map<*, *> -> put(key, buildNestedJson(value as Map<String, Any>))
                    is JsonElement -> put(key, value)
                }
            }
        }
    }

    // ─── Dictionary Serialization ────────────────────────────

    /**
     * Serializes a [BinaryDictionary] to binary format.
     * Format: repeated (varint_tag, string_path, varint_type_hint) tuples.
     */
    private fun serializeDictionary(dict: BinaryDictionary): ByteArray {
        val writer = BinaryWriter()
        for ((tag, path) in dict.fieldMappings.entries.sortedBy { it.key }) {
            // Field tag number
            writer.writeInt64(1, tag.toLong())
            // JSON key path
            writer.writeString(2, path)
            // Type hint
            val typeHint = dict.typeHints[tag] ?: FieldType.STRING
            writer.writeInt64(3, typeHint.value.toLong())
        }
        for (value in dict.valueDictionary) {
            writer.writeString(4, value)
        }
        return writer.toByteArray()
    }

    /**
     * Deserializes a [BinaryDictionary] from binary format.
     */
    private fun deserializeDictionary(bytes: ByteArray, dictId: String): BinaryDictionary {
        val reader = BinaryReader(bytes)
        val fieldMappings = mutableMapOf<Int, String>()
        val typeHints = mutableMapOf<Int, FieldType>()
        val valueDictionary = mutableListOf<String>()

        var currentTag = 0
        var currentPath = ""

        while (!reader.isAtEnd()) {
            val tag = reader.readTag()
            if (tag == 0) break
            val fieldNumber = WireFormat.fieldNumber(tag)

            when (fieldNumber) {
                1 -> currentTag = reader.readVarint().toInt()
                2 -> {
                    currentPath = reader.readString()
                    fieldMappings[currentTag] = currentPath
                }
                3 -> {
                    val typeValue = reader.readVarint().toInt()
                    typeHints[currentTag] = FieldType.fromValue(typeValue)
                }
                4 -> {
                    valueDictionary.add(reader.readString())
                }
                else -> reader.skipField(WireFormat.wireType(tag))
            }
        }

        val version = try {
            dictId.substringAfterLast("_v").toInt()
        } catch (_: Exception) { 1 }

        return BinaryDictionary(
            dictId = dictId,
            version = version,
            fieldMappings = fieldMappings,
            typeHints = typeHints,
            valueDictionary = valueDictionary,
        )
    }

    // ─── Dict Sync ───────────────────────────────────────────

    fun shouldIncludeDict(serverDictId: String, clientDictId: String?): Boolean {
        if (clientDictId == null) return true
        return clientDictId != serverDictId
    }

    fun registerDictionary(dictionary: BinaryDictionary) {
        dictStore[dictionary.schemaName] = dictionary
    }

    fun getDictId(schemaName: String): String? = dictStore[schemaName]?.dictId

    /**
     * Result of decoding a binary frame.
     */
    data class DecompactResult(
        val data: JsonElement,
        val dictId: String,
        val version: Int,
        val encoding: EncodingType,
    )
}
