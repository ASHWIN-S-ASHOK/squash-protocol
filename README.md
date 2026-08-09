# SQUASH - Hybrid JSON Compact Protocol

**SQUASH** is a high-performance, schema-less data serialization protocol designed to bridge the gap between the flexibility of JSON and the extreme density of binary formats like Protobuf. 

Unlike traditional formats (MessagePack, CBOR) that still transmit string keys over the wire, or rigid formats (Protobuf, gRPC) that require pre-compiled schema files, **SQUASH dynamically deduces schemas on the fly**, caches them, and strips out all structural overhead.

The result? Payload sizes drop by **50% to 68%**, effortlessly.

---

## 🚀 The Two Modes of SQUASH

SQUASH is built for the modern stack, offering two distinct engine modes depending on your client constraints:

### 1. SQUASH v1: Positional JSON Arrays (Web & Browsers)
Designed for lightweight web clients where implementing a binary parser isn't feasible. SQUASH v1 transparently flattens complex nested JSON objects into **Positional Arrays**, completely stripping out string keys and `{}` braces while remaining 100% valid JSON. 
* **Benefit:** Web clients can decode payloads natively using `JSON.parse()` at near-binary compression rates.

### 2. SQUASH v2: Binary Engine (Mobile & Microservices)
Designed for native mobile apps (iOS/Android) and server-to-server microservices (Python/Kotlin). SQUASH v2 serializes data into a custom byte stream utilizing **ZigZag Integer Encoding**, **Varint Tags**, and highly aggressive **String Interning**.
* **Benefit:** Absolute maximum data density. Massive arrays of objects with repeated strings are compressed to a fraction of their original size.

---

## 📊 Benchmarks

*Tests run on a standard dictionary mapping containing various nested objects and primitive arrays.*

| Payload Type | Format | Size | Savings | Time (ms) |
|---|---|---|---|---|
| **Large Array (500 Users)** | Raw JSON | 117.0 KB | 0% | 0.55 |
| | SQUASH v1 (Positional JSON) | 66.0 KB | **43.5%** | 1.95 |
| | SQUASH v2 (Binary) | 38.0 KB | **67.5%** | 7.00 |
| | | | | |
| **Massive Dictionary (~500KB)** | Raw JSON | 611.5 KB | 0% | 2.97 |
| | SQUASH v1 (Positional JSON) | 294.2 KB | **52.0%** | 10.64 |
| | SQUASH v2 (Binary) | 294.7 KB | **51.8%** | 35.30 |
| | | | | |
| **Worst-case (All Unique Keys)**| Raw JSON | 187.7 KB | 0% | 0.67 |
| | SQUASH v1 (Positional JSON) | 98.9 KB | **47.3%** | 1.85 |
| | SQUASH v2 (Binary) | 99.9 KB | **46.8%** | 5.41 |

> **Note:** Because SQUASH v1 delegates its serialization to Python's highly optimized native C-backend, it executes significantly faster than v2 Binary while maintaining incredible compression on dense objects!

---

## 🆚 Why SQUASH? (Compared to Global Standards)

1. **vs. Protobuf / gRPC:**
   * Protobuf requires you to define `.proto` schemas and compile code for every client. SQUASH is **schema-less**. You pass standard JSON to the engine, and it dynamically maps and caches the schema on the fly. No code generation required.
2. **vs. MessagePack / CBOR / BSON:**
   * MessagePack is a binary representation of JSON, but it *still transmits the string keys* (e.g. `"email"`, `"active"`) for every single object in an array. SQUASH deduplicates keys and structural overhead globally, destroying MessagePack in array compression.
3. **vs. GZIP / Brotli:**
   * Network compression is fantastic, but the client still has to allocate memory to parse a massive JSON string. SQUASH v1 Positional Arrays parse directly into lightweight native arrays, dramatically reducing the memory footprint on low-end devices. (SQUASH can also be used *alongside* GZIP for compounding gains).

---

## 💻 Quickstart (Python Middleware)

Adding SQUASH to your backend is as simple as adding a single line of middleware. When a client sends the `Accept-Encoding: squash` header, the server automatically intercepts the JSON response and compresses it.

```python
from fastapi import FastAPI
from squash.middleware import SquashMiddleware

app = FastAPI()

# Transparently compress all outgoing JSON responses
app.add_middleware(SquashMiddleware, schema_name="api_default")

@app.get("/users")
def get_users():
    return {"users": [...]} # Returns as compressed SQUASH!
```

---

## 🏗 Repository Structure

- `/squash-core/` - Kotlin Multiplatform core library (JVM, iOS, Android, JS/Wasm).
- `/squash-python/` - Python implementation & FastAPI middleware.
- `/squash-sample/` - Example projects demonstrating client/server integration.
- `/docs/` - Formal Protocol Specifications.

## 🤝 Contributing
SQUASH is open-source and welcomes contributions! Please read our contributing guidelines before submitting pull requests.
