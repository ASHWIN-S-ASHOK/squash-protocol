package com.squash.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/**
 * SQUASH protocol envelope — the top-level wire format for all SQUASH payloads.
 *
 * ```json
 * {
 *   "__meta": { "v": 1, "dictId": "user_v1", "encoding": "map" },
 *   "__dict": { "a": "user.name", "b": "user.email" },
 *   "d": { "a": "Ashwin", "b": "ashwin@email.com" }
 * }
 * ```
 */
@Serializable
data class SquashEnvelope(
    @SerialName("__meta")
    val meta: SquashMeta,

    @SerialName("__dict")
    val dict: Map<String, String>? = null,

    @SerialName("d")
    val data: JsonElement,
)

/**
 * Protocol metadata block carried inside every SQUASH envelope.
 *
 * @property version Protocol version (currently always `1`).
 * @property dictId  Dictionary identifier in `{schema}_v{version}` format.
 * @property encoding Encoding mode — currently only `"map"` is supported.
 */
@Serializable
data class SquashMeta(
    @SerialName("v")
    val version: Int = 1,

    @SerialName("dictId")
    val dictId: String,

    @SerialName("encoding")
    val encoding: String = "map",
)
