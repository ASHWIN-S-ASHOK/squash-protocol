#!/usr/bin/env python3
"""
Standalone test runner for SQUASH v2 Binary Protocol.

Tests Varint, BinaryWriter/Reader, VarintKeyMapper, and BinarySquashEngine.
Includes benchmark comparison of Raw JSON vs SQUASH v1 vs SQUASH v2.
"""

from __future__ import annotations

import json
import sys
import os
import traceback
import time

# Add squash-python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "squash-python"))

from squash.v2.varint import Varint
from squash.v2.wire import BinaryWriter, BinaryReader, WireFormat
from squash.v2.binary_dictionary import BinaryDictionary, FieldType, EncodingType
from squash.v2.key_mapper import VarintKeyMapper
from squash.v2.binary_engine import BinarySquashEngine
from squash.engine import SquashEngine


passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")


def run_tests():
    global passed, failed

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 Varint Tests")
    print("─" * 50)

    # Single-byte values (0-127)
    test("encode(0)", Varint.encode(0) == b"\x00")
    test("encode(1)", Varint.encode(1) == b"\x01")
    test("encode(127)", Varint.encode(127) == b"\x7f")

    # Two-byte values
    enc128 = Varint.encode(128)
    test("encode(128) is 2 bytes", len(enc128) == 2)
    test("encode(128) value", enc128 == bytes([0x80, 0x01]))

    enc300 = Varint.encode(300)
    test("encode(300) is 2 bytes", len(enc300) == 2)
    test("encode(300) value", enc300 == bytes([0xAC, 0x02]))

    # Three-byte values
    enc16384 = Varint.encode(16384)
    test("encode(16384) is 3 bytes", len(Varint.encode(16384)) == 3)

    # ZigZag encoding
    test("zigzag(0)", Varint.encode_zigzag(0) == 0)
    test("zigzag(-1)", Varint.encode_zigzag(-1) == 1)
    test("zigzag(1)", Varint.encode_zigzag(1) == 2)
    test("zigzag(-2)", Varint.encode_zigzag(-2) == 3)
    test("zigzag(2147483647)", Varint.encode_zigzag(2147483647) == 4294967294)
    test("zigzag(-2147483648)", Varint.encode_zigzag(-2147483648) == 4294967295)
    
    test("decode_zigzag(0)", Varint.decode_zigzag(0) == 0)
    test("decode_zigzag(1)", Varint.decode_zigzag(1) == -1)
    test("decode_zigzag(2)", Varint.decode_zigzag(2) == 1)
    test("decode_zigzag(3)", Varint.decode_zigzag(3) == -2)

    # Round-trips
    for v in [0, 1, 127, 128, 255, 300, 16383, 16384, 2097151, 2**31 - 1]:
        val, consumed = Varint.decode(Varint.encode(v))
        test(f"roundtrip({v})", val == v, f"got {val}")

    # Decode from offset
    prefix = b"\xff\xff"
    varint_bytes = Varint.encode(42)
    combined = prefix + varint_bytes
    val, consumed = Varint.decode(combined, offset=2)
    test("decode from offset", val == 42 and consumed == 1)

    # Field tags 1-15 → single byte
    for fn in range(1, 16):
        for wt in [0, 1, 2, 5]:
            tag = (fn << 3) | wt
            test(f"tag(fn={fn},wt={wt}) single byte", len(Varint.encode(tag)) == 1)

    # Field 16 → two bytes
    tag16 = (16 << 3) | 2  # = 130
    test("tag(fn=16,wt=2) two bytes", len(Varint.encode(tag16)) == 2)

    # Negative value raises
    try:
        Varint.encode(-1)
        test("negative raises", False, "Should have raised")
    except ValueError:
        test("negative raises ValueError", True)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 BinaryWriter / BinaryReader Tests")
    print("─" * 50)

    # String round-trip
    w = BinaryWriter()
    w.write_string(1, "Hello, SQUASH!")
    r = BinaryReader(w.to_bytes())
    tag = r.read_tag()
    test("string: field_number", WireFormat.field_number(tag) == 1)
    test("string: wire_type", WireFormat.wire_type(tag) == WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
    test("string: value", r.read_string() == "Hello, SQUASH!")
    test("string: at_end", r.is_at_end())

    # Int round-trip
    w = BinaryWriter()
    w.write_int64(2, 42)
    r = BinaryReader(w.to_bytes())
    tag = r.read_tag()
    test("int: field_number", WireFormat.field_number(tag) == 2)
    test("int: value", r.read_varint() == 42)

    # Bool round-trip
    w = BinaryWriter()
    w.write_bool(3, True)
    w.write_bool(4, False)
    r = BinaryReader(w.to_bytes())
    r.read_tag()
    test("bool: true", r.read_bool() is True)
    r.read_tag()
    test("bool: false", r.read_bool() is False)

    # Double round-trip
    w = BinaryWriter()
    w.write_double(5, 3.14159265)
    r = BinaryReader(w.to_bytes())
    tag = r.read_tag()
    test("double: field_number", WireFormat.field_number(tag) == 5)
    test("double: value", r.read_double() == 3.14159265)

    # Bytes round-trip
    w = BinaryWriter()
    w.write_bytes(6, b"\x01\x02\x03\x04")
    r = BinaryReader(w.to_bytes())
    r.read_tag()
    test("bytes: value", r.read_bytes() == b"\x01\x02\x03\x04")

    # Multi-field round-trip
    w = BinaryWriter()
    w.write_string(1, "Ashwin")
    w.write_string(2, "ashwin@email.com")
    w.write_int64(3, 28)
    w.write_bool(4, True)
    w.write_double(5, 99.99)
    r = BinaryReader(w.to_bytes())
    test("multi: f1", WireFormat.field_number(r.read_tag()) == 1 and r.read_string() == "Ashwin")
    test("multi: f2", WireFormat.field_number(r.read_tag()) == 2 and r.read_string() == "ashwin@email.com")
    test("multi: f3", WireFormat.field_number(r.read_tag()) == 3 and r.read_varint() == 28)
    test("multi: f4", WireFormat.field_number(r.read_tag()) == 4 and r.read_bool() is True)
    test("multi: f5", WireFormat.field_number(r.read_tag()) == 5 and r.read_double() == 99.99)
    test("multi: at_end", r.is_at_end())

    # Skip unknown fields
    w = BinaryWriter()
    w.write_string(1, "known")
    w.write_int64(99, 12345)
    w.write_string(2, "also known")
    r = BinaryReader(w.to_bytes())
    tag1 = r.read_tag()
    test("skip: f1", WireFormat.field_number(tag1) == 1 and r.read_string() == "known")
    tag2 = r.read_tag()
    test("skip: unknown fn", WireFormat.field_number(tag2) == 99)
    r.skip_field(WireFormat.wire_type(tag2))
    tag3 = r.read_tag()
    test("skip: f2", WireFormat.field_number(tag3) == 2 and r.read_string() == "also known")

    # Empty string
    w = BinaryWriter()
    w.write_string(1, "")
    r = BinaryReader(w.to_bytes())
    r.read_tag()
    test("empty string", r.read_string() == "")

    # Large string
    long_str = "x" * 1000
    w = BinaryWriter()
    w.write_string(1, long_str)
    r = BinaryReader(w.to_bytes())
    r.read_tag()
    test("large string", r.read_string() == long_str)

    # Reset
    w = BinaryWriter()
    w.write_string(1, "test")
    test("writer size > 0", w.size > 0)
    w.reset()
    test("writer reset", w.size == 0)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 VarintKeyMapper Tests")
    print("─" * 50)

    # Build from paths
    d = VarintKeyMapper.build_dictionary("user", 1, ["name", "email", "age"])
    test("dict_id", d.dict_id == "user_v1")
    test("version", d.version == 1)
    test("field_count", d.field_count == 3)
    test("tag 1", d.field_mappings[1] == "name")
    test("tag 2", d.field_mappings[2] == "email")
    test("tag 3", d.field_mappings[3] == "age")

    # Reverse mapping
    test("reverse name", d.reverse_mappings["name"] == 1)
    test("reverse email", d.reverse_mappings["email"] == 2)

    # Type inference
    sample = {"name": "Ashwin", "age": 28, "active": True, "score": 99.5}
    d2 = VarintKeyMapper.build_dictionary(
        "typed", 1, ["name", "age", "active", "score"], sample
    )
    test("type: string", d2.type_hints[1] == FieldType.STRING)
    test("type: int", d2.type_hints[2] == FieldType.INT64)
    test("type: bool", d2.type_hints[3] == FieldType.BOOL)
    test("type: double", d2.type_hints[4] == FieldType.DOUBLE)

    # Schema name extraction
    test("schema_name", d.schema_name == "user")

    # 15 fields → single-byte range
    paths15 = [f"field{i}" for i in range(1, 16)]
    d15 = VarintKeyMapper.build_dictionary("wide", 1, paths15)
    test("15 fields", d15.field_count == 15)
    for tag in range(1, 16):
        test(f"tag {tag} exists", tag in d15.field_mappings)

    # From v1 dictionary
    v1_mapping = {"a": "name", "b": "email"}
    d_v2 = VarintKeyMapper.from_v1_dictionary(v1_mapping, "user_v1", 1)
    test("v1→v2 tag 1", d_v2.field_mappings[1] == "name")   # 'a' → "name" (sorted first)
    test("v1→v2 tag 2", d_v2.field_mappings[2] == "email")  # 'b' → "email" (sorted second)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 BinarySquashEngine Tests")
    print("─" * 50)

    # Flat payload round-trip
    engine = BinarySquashEngine()
    original = {"name": "Ashwin", "email": "a@b.com"}
    frame = engine.to_binary_frame(original, "user")
    result = engine.from_binary_frame(frame)
    test("flat: name", result.data["name"] == "Ashwin")
    test("flat: email", result.data["email"] == "a@b.com")
    test("flat: version", result.version == 2)
    test("flat: dict_id", result.dict_id == "user_v1")
    test("flat: encoding", result.encoding == EncodingType.BINARY_MAP)

    # Nested payload round-trip
    engine2 = BinarySquashEngine()
    nested = {
        "user": {
            "name": "Ashwin",
            "address": {"city": "Mumbai", "zip": "400001"},
        }
    }
    frame = engine2.to_binary_frame(nested, "profile")
    result = engine2.from_binary_frame(frame)
    test("nested: name", result.data["user"]["name"] == "Ashwin")
    test("nested: city", result.data["user"]["address"]["city"] == "Mumbai")
    test("nested: zip", result.data["user"]["address"]["zip"] == "400001")

    # Complex diverse JSON (nulls, primitives arrays, mixed types)
    complex_data = {
        "uuid": "123e4567",
        "metadata": {"version": 1, "author": "admin", "deleted": None},
        "flags": [True, False, True],
        "scores": [99.9, 85.5],
        "notes": None,
    }
    frame_complex = engine.to_binary_frame(complex_data, "complex_test")
    res_complex = engine.from_binary_frame(frame_complex)
    test("complex: string", res_complex.data["uuid"] == "123e4567")
    test("complex: null in dict", res_complex.data.get("metadata", {}).get("deleted") is None)
    test("complex: array of bool", res_complex.data["flags"] == [True, False, True])
    test("complex: array of float", res_complex.data["scores"] == [99.9, 85.5])
    test("complex: top-level null", res_complex.data.get("notes") is None)

    # Typed payload (type hints via Pydantic or schema)
    engine3 = BinarySquashEngine()
    typed = {"name": "Ashwin", "age": 28, "active": True, "score": 99.5}
    frame = engine3.to_binary_frame(typed, "typed")
    result = engine3.from_binary_frame(frame)
    test("typed: name", result.data["name"] == "Ashwin")
    test("typed: age", result.data["age"] == 28)
    test("typed: active", result.data["active"] is True)
    test("typed: score", result.data["score"] == 99.5)

    # Dict omitted when client is current
    engine4 = BinarySquashEngine()
    data4 = {"name": "Ashwin"}
    frame1 = engine4.to_binary_frame(data4, "user")
    frame2 = engine4.to_binary_frame(data4, "user", client_dict_id="user_v1")
    test("no-dict smaller", len(frame2) < len(frame1), f"{len(frame2)} vs {len(frame1)}")
    result4 = engine4.from_binary_frame(frame2)
    test("no-dict decode", result4.data["name"] == "Ashwin")

    # Missing dict raises
    engine5 = BinarySquashEngine()
    try:
        engine5.from_binary_frame(frame2)  # No cache in fresh engine
        test("missing dict raises", False, "Should have raised")
    except ValueError:
        test("missing dict raises ValueError", True)

    # Register dictionary
    engine6 = BinarySquashEngine()
    d_reg = VarintKeyMapper.build_dictionary("reg", 1, ["x", "y"])
    engine6.register_dictionary(d_reg)
    test("register dict", engine6.get_dict_id("reg") == "reg_v1")

    # ═══════════════════════════════════════════════════════════
    print("\n📊 Benchmark: Raw JSON vs SQUASH v1 vs SQUASH v2")
    print("─" * 50)

    big_payload = {
        "user": {
            "id": 1,
            "name": "Ashwin Kumar",
            "email": "ashwin@email.com",
            "age": 28,
            "is_active": True,
            "address": {
                "street": "123 MG Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "zip_code": "400001",
                "country": "India",
            },
            "tags": ["developer", "kotlin", "python"],
        }
    }

    complex_payload = {
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "metadata": {"version": 1, "author": "admin", "deleted": None},
        "flags": [True, False, True, True],
        "scores": [99.9, 85.5, 42.0],
        "settings": {"dark_mode": True, "notifications": False},
        "notes": None,
    }

    large_array_payload = [big_payload["user"] for _ in range(500)]

    massive_payload = {
        f"user_{i}": {
            "id": i,
            "name": f"User Name {i}",
            "email": f"user_{i}@example.com",
            "active": True,
            "settings": {"dark_mode": True, "notifications": False},
            "tags": ["developer", "tester"]
        } for i in range(3500)
    }

    unique_keys_payload = {
        f"unique_key_{i}": f"unique_value_{i}" for i in range(5000)
    }

    payloads = [
        ("Standard Profile", big_payload, "user_profile"),
        ("Complex Profile", complex_payload, "complex_profile"),
        ("Large Array (500 Users)", large_array_payload, "large_array"),
        ("Massive Dictionary (~500KB)", massive_payload, "massive_dict"),
        ("All Unique Keys (Worst-case)", unique_keys_payload, "unique_keys_dict"),
    ]

    for name, payload, schema in payloads:
        print(f"\n  ➤ Payload: {name}")

        # Raw JSON
        start_t = time.perf_counter()
        raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        raw_time = (time.perf_counter() - start_t) * 1000
        raw_size = len(raw_json)

        # SQUASH v1 (with dict — first request)
        v1_engine = SquashEngine()
        start_t = time.perf_counter()
        v1_envelope = v1_engine.encode(payload, schema)
        v1_with_dict_size = len(json.dumps(v1_envelope, separators=(",", ":")).encode("utf-8"))
        v1_with_dict_time = (time.perf_counter() - start_t) * 1000

        # SQUASH v1 (no dict — subsequent request)
        start_t = time.perf_counter()
        v1_no_dict = v1_engine.encode(payload, schema, client_dict_id=v1_envelope["__meta"]["dictId"])
        v1_no_dict_size = len(json.dumps(v1_no_dict, separators=(",", ":")).encode("utf-8"))
        v1_no_dict_time = (time.perf_counter() - start_t) * 1000

        # SQUASH v2 (with dict — first request)
        v2_engine = BinarySquashEngine()
        start_t = time.perf_counter()
        v2_with_dict = v2_engine.to_binary_frame(payload, schema)
        v2_with_dict_size = len(v2_with_dict)
        v2_with_dict_time = (time.perf_counter() - start_t) * 1000

        # SQUASH v2 (no dict — subsequent request)
        start_t = time.perf_counter()
        v2_no_dict = v2_engine.to_binary_frame(payload, schema, client_dict_id=f"{schema}_v1")
        v2_no_dict_size = len(v2_no_dict)
        v2_no_dict_time = (time.perf_counter() - start_t) * 1000

        # Verify v2 round-trip
        v2_result = v2_engine.from_binary_frame(v2_with_dict)

        print(f"    {'Format':<35} {'Size':>8} {'%':>6} {'Time(ms)':>10}")
        print(f"    {'─' * 62}")
        print(f"    {'Raw JSON':<35} {raw_size:>6} B {'100.0%':>6} {raw_time:>10.2f}")
        print(f"    {'SQUASH v1 JSON (with __dict)':<35} {v1_with_dict_size:>6} B {100*v1_with_dict_size/raw_size:>5.1f}% {v1_with_dict_time:>10.2f}")
        print(f"    {'SQUASH v1 JSON (cached dict)':<35} {v1_no_dict_size:>6} B {100*v1_no_dict_size/raw_size:>5.1f}% {v1_no_dict_time:>10.2f}")
        print(f"    {'SQUASH v2 Binary (with dict)':<35} {v2_with_dict_size:>6} B {100*v2_with_dict_size/raw_size:>5.1f}% {v2_with_dict_time:>10.2f}")
        print(f"    {'SQUASH v2 Binary (cached dict)':<35} {v2_no_dict_size:>6} B {100*v2_no_dict_size/raw_size:>5.1f}% {v2_no_dict_time:>10.2f}")
        print()
        print(f"    🏆 v2 cached savings: {100*(1-v2_no_dict_size/raw_size):.1f}% smaller than raw JSON")

    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*50}\n")

    return failed == 0


if __name__ == "__main__":
    try:
        success = run_tests()
    except Exception:
        traceback.print_exc()
        success = False
    sys.exit(0 if success else 1)
