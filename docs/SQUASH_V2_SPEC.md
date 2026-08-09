# SQUASH v2 — Binary Protocol Specification

**Version**: 2.0  
**Status**: Draft  
**Date**: 2026-08-09  
**Authors**: SQUASH Monorepo Contributors

---

## 1. Introduction

SQUASH v2 extends the Hybrid JSON Compact Protocol with a **binary transport mode** that replaces UTF-8 JSON key-value strings with Protocol Buffers wire-format binary frames. This achieves ~40-80% payload size reduction over raw JSON while maintaining backward compatibility with SQUASH v1.

### 1.1. Design Goals

1. **Binary Transport**: Replace JSON envelope with Protobuf wire-format binary blobs.
2. **Varint Field Indexing**: Map dictionary paths to 1-based integer field tags (1–15 are single-byte).
3. **Hybrid Negotiation**: HTTP content negotiation for seamless v1 ↔ v2 coexistence.
4. **Streaming Support**: Binary format compatible with gRPC / HTTP/2 frame streaming.
5. **Zero Breaking Changes**: All v1 code paths remain unchanged.

---

## 2. Terminology

| Term | Definition |
|------|-----------|
| **Field Tag** | A 1-based integer identifying a field in the binary dictionary |
| **Varint** | LEB128 unsigned variable-length integer encoding |
| **Wire Type** | Protobuf encoding hint (0=varint, 1=fixed64, 2=length-delimited, 5=fixed32) |
| **Binary Frame** | The complete v2 binary envelope sent over the wire |
| **Dictionary Sync** | Server-client coordination to avoid retransmitting known dictionaries |

---

## 3. Wire Format

### 3.1. Varint Encoding (LEB128)

Unsigned integers are encoded using LEB128 (Little-Endian Base 128):

```
Each byte uses 7 data bits + 1 continuation bit (MSB):
  MSB=1 → more bytes follow
  MSB=0 → final byte

Value 300 (0x012C):
  Byte 1: 10101100  (0xAC) — data: 0101100, MSB=1
  Byte 2: 00000010  (0x02) — data: 0000010, MSB=0
```

**Size characteristics**:

| Value Range | Bytes | SQUASH v2 Usage |
|------------|------:|---------------|
| 0 – 127 | 1 | Field tags 1–15 (most common fields) |
| 128 – 16,383 | 2 | Field tags 16–2047 |
| 16,384 – 2,097,151 | 3 | Large integer values |

### 3.2. Field Tag Encoding

Each field in the binary payload is prefixed with a tag that combines the field number and wire type:

```
tag = (field_number << 3) | wire_type
```

Encoded as a Varint. For field numbers 1–15 with any wire type, this is always a **single byte**.

### 3.3. Wire Types

| ID | Type | Size | Used For |
|---:|------|------|----------|
| 0 | Varint | Variable | int64, bool, enum |
| 1 | Fixed64 | 8 bytes | double |
| 2 | Length-delimited | Variable | string, bytes, embedded |
| 5 | Fixed32 | 4 bytes | float |

### 3.4. Value Encoding

| JSON Type | Wire Type | Encoding |
|-----------|-----------|----------|
| `string` | 2 | `<varint_length> <utf8_bytes>` |
| `number` (integer) | 0 | `<varint_value>` |
| `number` (float) | 1 | `<8_byte_le_ieee754>` |
| `boolean` | 0 | `<varint: 0 or 1>` |
| `null` | — | Field omitted entirely |
| `array` / nested `object` | 2 | `<varint_length> <json_string_bytes>` |

---

## 4. Binary Frame Structure

### 4.1. Frame Layout

A complete SQUASH v2 binary frame is a sequence of Protobuf-style tagged fields:

```
┌─────────────────────────────────────────────────────┐
│ Tag 1 (varint): version        = 2                  │
│ Tag 2 (string): dictId         = "user_v1"          │
│ Tag 3 (varint): encoding       = 1 (BINARY_MAP)     │
│ Tag 4 (bytes):  dict_data      = <serialized dict>  │  ← Optional
│ Tag 5 (bytes):  payload        = <binary payload>   │
└─────────────────────────────────────────────────────┘
```

### 4.2. Frame Field Definitions

| Tag | Name | Wire Type | Required | Description |
|----:|------|-----------|----------|-------------|
| 1 | `version` | varint (0) | Yes | Protocol version, always `2` |
| 2 | `dict_id` | string (2) | Yes | Dictionary identifier |
| 3 | `encoding` | varint (0) | Yes | Encoding type enum |
| 4 | `dict_data` | bytes (2) | No | Serialized dictionary (omitted when client cache is current) |
| 5 | `payload` | bytes (2) | Yes | Binary-encoded payload |

### 4.3. Encoding Types

| Value | Name | Description |
|------:|------|-------------|
| 0 | `UNSPECIFIED` | Invalid |
| 1 | `BINARY_MAP` | Each field is Varint-tagged (primary mode) |
| 2 | `BINARY_ARRAY` | Ordered packed values, no individual tags (future) |
| 3 | `PROTOBUF_DYNAMIC` | Full Protobuf dynamic descriptor (future) |

---

## 5. Dictionary Format

### 5.1. Dictionary Structure

A v2 dictionary maps 1-based integer field tags to canonical JSON key paths:

```
{
  1 → "user.name"          (FieldType: STRING)
  2 → "user.email"         (FieldType: STRING)
  3 → "user.age"           (FieldType: INT64)
  4 → "user.is_active"     (FieldType: BOOL)
  5 → "user.address.city"  (FieldType: STRING)
}
```

### 5.2. FieldType Hints

| Value | Name | Wire Type | Description |
|------:|------|-----------|-------------|
| 0 | `UNSPECIFIED` | — | Default to STRING behavior |
| 1 | `STRING` | 2 | UTF-8 string |
| 2 | `INT64` | 0 | Signed 64-bit integer |
| 3 | `DOUBLE` | 1 | IEEE 754 double |
| 4 | `BOOL` | 0 | Boolean (varint 0/1) |
| 5 | `BYTES` | 2 | Raw byte array |
| 6 | `EMBEDDED` | 2 | Nested SQUASH object |

### 5.3. Varint Key Mapper Algorithm

The Varint Key Mapper translates v1 Base62 dictionaries to v2 integer tags:

```
INPUT:  v1 dictionary = { "a" → "user.name", "b" → "user.email", "c" → "user.age" }

STEP 1: Sort entries by Base62 key (alphabetical)
        sorted = [("a", "user.name"), ("b", "user.email"), ("c", "user.age")]

STEP 2: Assign 1-based sequential tags
        tag_map = { 1 → "user.name", 2 → "user.email", 3 → "user.age" }

STEP 3: Infer type hints from sample JSON (optional)
        type_hints = { 1 → STRING, 2 → STRING, 3 → INT64 }

OUTPUT: BinaryDictionary(dict_id="user_v1", field_mappings=tag_map, type_hints=type_hints)
```

### 5.4. Dictionary Serialization

Dictionaries embedded in frames are serialized as repeating field triplets:

```
For each entry:
  Tag 1 (varint): field_tag_number
  Tag 2 (string): json_key_path
  Tag 3 (varint): field_type_hint
```

---

## 6. Content Negotiation

### 6.1. HTTP Headers

| Header | Value | Meaning |
|--------|-------|---------|
| `Accept` | `application/squash+proto` | Client prefers binary |
| `Accept` | `application/squash+json` | Client prefers JSON (v1) |
| `Accept` | `application/squash+proto, application/squash+json` | Both supported, binary preferred |
| `Content-Type` | `application/squash+proto` | Response is binary |
| `Content-Type` | `application/squash+json` | Response is JSON (v1) |
| `Content-Encoding` | `squash` | Legacy v1 indicator (backward compat) |
| `X-SQUASH-DictId` | `user_v1` | Client's cached dictionary ID |

### 6.2. Negotiation Flow

```
Client                                      Server
  │                                           │
  │  GET /api/users                           │
  │  Accept: application/squash+proto           │
  │  X-SQUASH-DictId: (none)                    │
  │ ─────────────────────────────────────────► │
  │                                           │
  │  200 OK                                   │
  │  Content-Type: application/squash+proto     │
  │  X-SQUASH-DictId: users_v1                  │
  │  Body: <binary frame WITH dict>           │
  │ ◄───────────────────────────────────────── │
  │                                           │
  │  GET /api/users                           │
  │  Accept: application/squash+proto           │
  │  X-SQUASH-DictId: users_v1                  │
  │ ─────────────────────────────────────────► │
  │                                           │
  │  200 OK                                   │
  │  Content-Type: application/squash+proto     │
  │  Body: <binary frame WITHOUT dict>        │
  │ ◄───────────────────────────────────────── │
```

---

## 7. Payload Encoding (BINARY_MAP)

### 7.1. Encoding Process

1. **Flatten** the JSON object to dot-notation key paths
2. **Resolve** each key path to its integer field tag via the dictionary
3. **Write** each value as a Protobuf-tagged field:

```
Input JSON:
{
  "user": {
    "name": "Ashwin",
    "email": "ashwin@email.com",
    "age": 28,
    "active": true
  }
}

Dictionary:
  1 → "user.name"    (STRING)
  2 → "user.email"   (STRING)
  3 → "user.age"     (INT64)
  4 → "user.active"  (BOOL)

Binary payload (hex):
  0A 06 41 73 68 77 69 6E        # tag=1,wt=2, len=6, "Ashwin"
  12 10 61 73 68 77 69 6E ...    # tag=2,wt=2, len=16, "ashwin@email.com"
  18 1C                          # tag=3,wt=0, varint=28
  20 01                          # tag=4,wt=0, varint=1 (true)
```

### 7.2. Decoding Process

1. **Read** tagged fields from the binary stream
2. **Look up** each field number in the dictionary to get the JSON key path
3. **Use** the type hint to correctly interpret the wire type
4. **Unflatten** dot-notation paths back to nested JSON

---

## 8. Streaming Protocol Support

The binary frame format is designed for streaming compatibility:

- **gRPC**: Each `SquashBinaryFrame` can be a gRPC message in a stream
- **HTTP/2**: Frames can be sent as individual DATA frames
- **WebSocket**: Each frame is a single binary WebSocket message
- **Server-Sent Events**: Not supported (binary format)

For streaming, the first frame in a stream MUST include the dictionary.
Subsequent frames in the same stream MAY omit it.

---

## 9. Backward Compatibility

| Feature | v1 | v2 |
|---------|----|----|
| Wire format | JSON | Protobuf binary |
| Key type | Base62 strings | Varint integers |
| Content-Type | `application/json` | `application/squash+proto` |
| Content-Encoding | `squash` | — |
| Envelope | `{"__meta":…,"__dict":…,"d":…}` | Binary frame tags 1-5 |
| Dict format | `{"a":"user.name"}` | `{1:"user.name"}` |

Servers MUST support both v1 and v2 simultaneously using content negotiation.
Clients MAY declare support for one or both modes.
