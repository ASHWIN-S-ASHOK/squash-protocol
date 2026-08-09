#!/usr/bin/env python3
"""
Standalone test runner for SQUASH core logic.

Runs without pytest or any external dependencies beyond pydantic.
Tests Base62, KeyCompactor, JsonTransformer, Engine, and DictionaryStore.
"""

from __future__ import annotations

import sys
import os
import traceback

# Add squash-python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "squash-python"))

from squash.base62 import Base62
from squash.compactor import JsonTransformer, KeyCompactor
from squash.dictionary import DictionaryBuilder, DictionaryStore, SquashDictionary
from squash.engine import SquashEngine
from squash.utils import flatten_dict, unflatten_dict, json_dumps, json_loads


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
    print("\n🔬 Base62 Tests")
    print("─" * 50)

    test("a=0", Base62.encode(0) == "a")
    test("b=1", Base62.encode(1) == "b")
    test("z=25", Base62.encode(25) == "z")
    test("A=26", Base62.encode(26) == "A")
    test("Z=51", Base62.encode(51) == "Z")
    test("0=52", Base62.encode(52) == "0")
    test("9=61", Base62.encode(61) == "9")
    test("aa=62", Base62.encode(62) == "aa")
    test("ab=63", Base62.encode(63) == "ab")
    test("a9=123", Base62.encode(123) == "a9")
    test("ba=124", Base62.encode(124) == "ba")

    keys = Base62.generate_keys(5)
    test("generate_keys(5)", keys == ["a", "b", "c", "d", "e"], str(keys))

    keys62 = Base62.generate_keys(62)
    test("62 unique single-char keys", len(set(keys62)) == 62)

    keys200 = Base62.generate_keys(200)
    test("200 unique keys", len(set(keys200)) == 200)

    try:
        Base62.encode(-1)
        test("negative raises", False, "Should have raised")
    except ValueError:
        test("negative raises", True)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 KeyCompactor Tests")
    print("─" * 50)

    paths = KeyCompactor.extract_key_paths({"name": "Ashwin", "email": "a@b.com"})
    test("flat keys", paths == ["name", "email"], str(paths))

    paths = KeyCompactor.extract_key_paths(
        {"user": {"name": "Ashwin", "address": {"city": "Mumbai", "zip": "400001"}}}
    )
    test(
        "nested keys",
        paths == ["user.name", "user.address.city", "user.address.zip"],
        str(paths),
    )

    paths = KeyCompactor.extract_key_paths(
        {"users": [{"name": "A", "age": 1}, {"name": "B", "age": 2}]}
    )
    test("array-of-objects keys", paths == ["users.name", "users.age"], str(paths))

    paths = KeyCompactor.extract_key_paths({"tags": ["a", "b"], "name": "x"})
    test("array-of-primitives", paths == ["tags", "name"], str(paths))

    mapping = KeyCompactor.build_mapping(["name", "email", "city"])
    test("build_mapping", mapping == {"a": "name", "b": "email", "c": "city"}, str(mapping))

    test("empty object", KeyCompactor.extract_key_paths({}) == [])

    paths = KeyCompactor.extract_key_paths({"a": {"b": {"c": {"d": "val"}}}})
    test("deeply nested", paths == ["a.b.c.d"], str(paths))

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 JsonTransformer Tests")
    print("─" * 50)

    # Compact flat
    data = {"name": "Ashwin", "email": "a@b.com"}
    reverse = {"name": "a", "email": "b"}
    result = JsonTransformer.compact(data, reverse)
    test("compact flat", result == {"a": "Ashwin", "b": "a@b.com"}, str(result))

    # Compact nested
    data = {"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}}
    reverse = {"user.name": "a", "user.address.city": "b"}
    result = JsonTransformer.compact(data, reverse)
    test("compact nested", result == {"a": "Ashwin", "b": "Mumbai"}, str(result))

    # Expand flat
    compacted = {"a": "Ashwin", "b": "a@b.com"}
    mapping = {"a": "name", "b": "email"}
    result = JsonTransformer.expand(compacted, mapping)
    test("expand flat", result == {"name": "Ashwin", "email": "a@b.com"}, str(result))

    # Expand nested
    compacted = {"a": "Ashwin", "b": "Mumbai"}
    mapping = {"a": "user.name", "b": "user.address.city"}
    result = JsonTransformer.expand(compacted, mapping)
    expected = {"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}}
    test("expand nested", result == expected, str(result))

    # Round-trip flat
    original = {"name": "Ashwin", "email": "a@b.com", "age": 28}
    reverse = {"name": "a", "email": "b", "age": "c"}
    mapping = {v: k for k, v in reverse.items()}
    compacted = JsonTransformer.compact(original, reverse)
    expanded = JsonTransformer.expand(compacted, mapping)
    test("roundtrip flat", expanded == original, str(expanded))

    # Round-trip nested
    original = {"user": {"name": "Ashwin", "address": {"city": "Mumbai", "zip": "400001"}}}
    reverse = {"user.name": "a", "user.address.city": "b", "user.address.zip": "c"}
    mapping = {v: k for k, v in reverse.items()}
    compacted = JsonTransformer.compact(original, reverse)
    expanded = JsonTransformer.expand(compacted, mapping)
    test("roundtrip nested", expanded == original, str(expanded))

    # Preserves primitives
    data = {"count": 42, "active": True, "name": "test"}
    reverse = {"count": "a", "active": "b", "name": "c"}
    result = JsonTransformer.compact(data, reverse)
    test("preserves primitives", result == {"a": 42, "b": True, "c": "test"}, str(result))

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 DictionaryStore Tests")
    print("─" * 50)

    store = DictionaryStore()
    d = SquashDictionary("user_v1", 1, {"a": "name", "b": "email"})
    test("put returns True", store.put(d) is True)
    test("get by schema", store.get("user") is not None)
    test("get by dict_id", store.get_by_dict_id("user_v1") is not None)
    test("is_current", store.is_current("user_v1"))
    test("not current for v2", not store.is_current("user_v2"))

    d2 = SquashDictionary("user_v2", 2, {"a": "name", "b": "email", "c": "age"})
    test("upgrade put", store.put(d2) is True)
    test("downgrade rejected", store.put(d) is False)
    test("get returns v2", store.get("user").dict_id == "user_v2")

    store.clear()
    test("clear empties store", store.size == 0)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 DictionaryBuilder Tests")
    print("─" * 50)

    d = DictionaryBuilder.build("user", 1, {"name": "Ashwin", "email": "a@b.com"})
    test("dict_id", d.dict_id == "user_v1")
    test("version", d.version == 1)
    test("mapping keys", "a" in d.mapping and "b" in d.mapping)
    test("mapping values", d.mapping["a"] == "name" and d.mapping["b"] == "email")

    d = DictionaryBuilder.build_from_paths("custom", 2, ["x", "y", "z"])
    test("from_paths dict_id", d.dict_id == "custom_v2")
    test("from_paths mapping", d.mapping == {"a": "x", "b": "y", "c": "z"}, str(d.mapping))

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 SquashEngine Tests")
    print("─" * 50)

    # Encode creates valid envelope
    engine = SquashEngine()
    original = {"name": "Ashwin", "email": "a@b.com"}
    envelope = engine.encode(original, "user")
    test("envelope has __meta", "__meta" in envelope)
    test("meta.v == 1", envelope["__meta"]["v"] == 1)
    test("meta.dictId", envelope["__meta"]["dictId"] == "user_v1")
    test("meta.encoding", envelope["__meta"]["encoding"] == "map")
    test("first encode has __dict", "__dict" in envelope)
    test("has data d", "d" in envelope)

    # Omits dict when current
    e2 = engine.encode(original, "user", client_dict_id="user_v1")
    test("omits dict when current", "__dict" not in e2)

    # Includes dict on mismatch
    e3 = engine.encode(original, "user", client_dict_id="user_v0")
    test("includes dict on mismatch", "__dict" in e3)

    # Decode with embedded dict
    decoded = engine.decode(envelope)
    test("decode name", decoded["name"] == "Ashwin")
    test("decode email", decoded["email"] == "a@b.com")

    # Decode with cached dict (no __dict in envelope)
    decoded2 = engine.decode(e2)
    test("decode cached", decoded2["name"] == "Ashwin")

    # Decode without dict or cache raises
    engine2 = SquashEngine()
    try:
        engine2.decode(e2)
        test("no dict raises", False, "Should have raised")
    except ValueError:
        test("no dict raises ValueError", True)

    # Full round-trip with nested data
    engine3 = SquashEngine()
    original = {"user": {"name": "Ashwin", "address": {"city": "Mumbai", "zip": "400001"}}}
    envelope = engine3.encode(original, "profile")
    decoded = engine3.decode(envelope)
    test("nested roundtrip name", decoded["user"]["name"] == "Ashwin")
    test("nested roundtrip city", decoded["user"]["address"]["city"] == "Mumbai")
    test("nested roundtrip zip", decoded["user"]["address"]["zip"] == "400001")

    # should_include_dict
    test("include when None", engine.should_include_dict("v1", None) is True)
    test("include on mismatch", engine.should_include_dict("v2", "v1") is True)
    test("exclude when match", engine.should_include_dict("v1", "v1") is False)

    # Register dictionary
    engine4 = SquashEngine()
    d = DictionaryBuilder.build_from_paths("reg", 1, ["x", "y"])
    engine4.register_dictionary(d)
    test("register dict", engine4.dict_store.get("reg") is not None)

    # ═══════════════════════════════════════════════════════════
    print("\n🔬 Utils Tests")
    print("─" * 50)

    flat = flatten_dict({"user": {"name": "A", "address": {"city": "M"}}})
    test("flatten", flat == {"user.name": "A", "user.address.city": "M"}, str(flat))

    nested = unflatten_dict({"user.name": "A", "user.address.city": "M"})
    expected = {"user": {"name": "A", "address": {"city": "M"}}}
    test("unflatten", nested == expected, str(nested))

    # json_dumps / json_loads round-trip
    data = {"key": "value", "num": 42}
    serialized = json_dumps(data)
    deserialized = json_loads(serialized)
    test("json round-trip", deserialized == data, str(deserialized))

    # ═══════════════════════════════════════════════════════════
    # Compression ratio demo
    print("\n📊 Compression Demo")
    print("─" * 50)
    engine5 = SquashEngine()
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
    envelope = engine5.encode(big_payload, "user_profile")
    orig_size = len(json_dumps(big_payload))
    compact_size = len(json_dumps(envelope))

    print(f"  Original:  {orig_size} bytes")
    print(f"  Compact:   {compact_size} bytes (with __dict)")

    # Second request (no dict) — much smaller
    envelope_no_dict = engine5.encode(big_payload, "user_profile", client_dict_id=envelope["__meta"]["dictId"])
    compact_no_dict_size = len(json_dumps(envelope_no_dict))
    print(f"  No dict:   {compact_no_dict_size} bytes (cached dict)")
    print(f"  Savings:   {100 * (1 - compact_no_dict_size / orig_size):.1f}%")

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
