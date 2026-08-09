# SQUASH Roadmap — v1 vs v2 Protocol Comparison

---

## Protocol Overview

| | SQUASH v1 | SQUASH v2 |
|---|---------|---------|
| **Wire Format** | JSON text (`application/json`) | Protobuf binary (`application/squash+proto`) |
| **Key Encoding** | Base62 strings (`"a"`, `"b"`, `"aa"`) | Varint integers (`1`, `2`, `16`) |
| **Envelope** | `{"__meta":{…},"__dict":{…},"d":{…}}` | Binary frame (tags 1–5) |
| **Type Awareness** | None — all values are JSON | FieldType hints (string, int64, double, bool, bytes, embedded) |
| **Content Negotiation** | `Accept-Encoding: squash` | `Accept: application/squash+proto` |
| **Streaming** | Not designed for streaming | gRPC / HTTP/2 / WebSocket compatible |
| **Implementation** | kotlinx.serialization.json | Manual Protobuf wire format (pure KMP + Python) |

---

## Size Comparison

Benchmark payload: User profile object (~10 fields, nested address)

| Format | First Request | Subsequent Requests |
|--------|:------------:|:-------------------:|
| **Raw JSON** | 242 B (100%) | 242 B (100%) |
| **SQUASH v1 (JSON)** | 482 B (199%) | 242 B (100%) |
| **SQUASH v2 (Binary)** | 364 B (150%) | **143 B (59%)** |

Key insight: v2's advantage grows dramatically on **repeated requests** (cached dictionaries), achieving **~41% savings** over raw JSON and v1.

With larger payloads (100+ fields), expected savings increase to **60-80%** due to:
- Varint tags (1 byte) vs JSON key strings (5-20 bytes each)
- Varint integers (1-3 bytes) vs JSON number strings (1-10 bytes)
- No JSON structural overhead (quotes, colons, commas, braces)

---

## Header Negotiation Rules

### Client Request Headers

```http
# v2 binary preferred, v1 JSON fallback
Accept: application/squash+proto, application/squash+json
Accept-Encoding: squash
X-SQUASH-DictId: users_v1
```

### Server Response Headers

```http
# v2 binary response
Content-Type: application/squash+proto
X-SQUASH-DictId: users_v1

# v1 JSON response (fallback)
Content-Type: application/json
Content-Encoding: squash
X-SQUASH-DictId: users_v1
```

### Decision Matrix

| Client `Accept` | Server Support | Response Format |
|-----------------|----------------|----------------|
| `application/squash+proto` | v2 ✓ | Binary |
| `application/squash+proto` | v2 ✗ | JSON (v1 fallback) |
| `application/squash+json` | v1 ✓ | JSON |
| `application/squash+proto, application/squash+json` | v2 ✓ | Binary (preferred) |
| `application/squash+proto, application/squash+json` | v2 ✗ | JSON |
| None / `application/json` | — | Raw JSON (no SQUASH) |

---

## Migration Guide

### Phase 1: Add v2 Support (Additive)

The v2 module lives in a separate `v2/` package — no v1 code is modified.

**Server (Python)**:
```python
from squash.v2 import BinarySquashEngine

engine = BinarySquashEngine()

# Check Accept header
if "application/squash+proto" in request.headers.get("accept", ""):
    frame = engine.to_binary_frame(data, "users", client_dict_id)
    return Response(content=frame, media_type="application/squash+proto")
else:
    # Fall back to v1 or raw JSON
    ...
```

**Client (Kotlin/Android)**:
```kotlin
val client = OkHttpClient.Builder()
    .addInterceptor(
        SquashOkHttpInterceptor(
            engine = SquashEngine(),
            binaryEngine = BinarySquashEngine(),
            preferBinary = true,
        )
    )
    .build()
```

### Phase 2: Binary-First (Optional)

Once all clients support v2, servers can default to binary responses:
- Set `preferBinary = true` on interceptors
- Configure middleware to default to `application/squash+proto`

### Phase 3: v1 Deprecation (Future)

After a migration period, v1 JSON mode can be deprecated:
- Remove `Accept-Encoding: squash` legacy header support
- Remove JSON envelope code paths
- Keep v2 binary as the sole SQUASH transport

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  SQUASH Stack                      │
├─────────────┬───────────────────────────────────┤
│  v1 (JSON)  │           v2 (Binary)              │
├─────────────┼───────────────────────────────────┤
│ Base62      │  Varint (LEB128)                   │
│ KeyCompactor│  VarintKeyMapper                   │
│ JsonTransf. │  BinaryWriter / BinaryReader       │
│ DictStore   │  BinaryDictionary                  │
│ SquashEngine  │  BinarySquashEngine                  │
├─────────────┴───────────────────────────────────┤
│        Content Negotiation Layer                 │
│  (OkHttp Interceptor / FastAPI Middleware)        │
└─────────────────────────────────────────────────┘
```

---

## File Inventory (v2 additions)

### Kotlin Multiplatform (`squash-core`)
| Path | Description |
|------|-------------|
| `v2/wire/Varint.kt` | LEB128 varint codec |
| `v2/wire/WireFormat.kt` | Wire type constants |
| `v2/wire/BinaryWriter.kt` | Frame writer |
| `v2/wire/BinaryReader.kt` | Frame reader |
| `v2/model/EncodingType.kt` | Encoding mode enum |
| `v2/model/FieldType.kt` | Type hint enum |
| `v2/model/BinaryDictionary.kt` | v2 dictionary model |
| `v2/engine/VarintKeyMapper.kt` | Base62 → integer mapper |
| `v2/engine/BinarySquashEngine.kt` | Binary encode/decode engine |

### Python (`squash-python`)
| Path | Description |
|------|-------------|
| `squash/v2/varint.py` | LEB128 varint codec |
| `squash/v2/wire.py` | Wire format + writer/reader |
| `squash/v2/binary_dictionary.py` | v2 dictionary + enums |
| `squash/v2/key_mapper.py` | Base62 → integer mapper |
| `squash/v2/binary_engine.py` | Binary encode/decode engine |
