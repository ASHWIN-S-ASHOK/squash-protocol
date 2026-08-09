#!/usr/bin/env python3
"""
SQUASH E2E Client Test — verifies the full client-server protocol loop.

This script tests all SQUASH protocol scenarios against the sample backend:
1. Non-SQUASH request → standard JSON response
2. First SQUASH request → envelope with __dict
3. Cached dict request → envelope without __dict
4. Dict version mismatch → envelope with updated __dict
5. Nested payload → proper compaction/expansion

Run the backend first:
    cd squash-sample/backend && uvicorn main:app --port 8000

Then run this script:
    python python_client.py
"""

from __future__ import annotations

import json
import sys
import os

# Add squash-python to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "squash-python"))

import requests

from squash.engine import SquashEngine
from squash.v2 import BinarySquashEngine

BASE_URL = "http://localhost:8000"
engine = SquashEngine()
binary_engine = BinarySquashEngine()


def print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_json(label: str, data: dict) -> None:
    print(f"\n  {label}:")
    print(f"  {json.dumps(data, indent=2, default=str)[:500]}")


def test_1_non_squash_request() -> bool:
    """Scenario 1: Client without SQUASH headers gets plain JSON."""
    print_header("Test 1: Non-SQUASH Client → Standard JSON")

    response = requests.get(f"{BASE_URL}/users/1")
    data = response.json()

    assert "__meta" not in data, "Non-SQUASH response should not have __meta"
    assert "name" in data, "Should have original 'name' key"
    assert data["name"] == "Ashwin Kumar"

    print_json("Response", data)
    print("\n  ✅ PASSED: Non-SQUASH client receives standard JSON")
    return True


def test_2_first_squash_request() -> bool:
    """Scenario 2: First SQUASH request gets envelope with __dict."""
    print_header("Test 2: First SQUASH Request → Envelope + Dict")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={"Accept-Encoding": "squash"},
    )
    data = response.json()

    assert "__meta" in data, "SQUASH response must have __meta"
    assert data["__meta"]["v"] == 1
    assert data["__meta"]["encoding"] == "map"
    assert "__dict" in data, "First request must include __dict"
    assert "d" in data, "Must have compacted data 'd'"

    # Verify SQUASH headers
    assert response.headers.get("content-encoding") == "squash"
    assert "x-squash-dictid" in response.headers

    print_json("Envelope", data)
    print(f"\n  Dict ID: {data['__meta']['dictId']}")
    print(f"  Dict keys: {len(data['__dict'])}")
    print(f"  Content-Encoding: {response.headers.get('content-encoding')}")

    # Decode the envelope
    decoded = engine.decode(data)
    assert decoded["name"] == "Ashwin Kumar"
    print_json("Decoded", decoded)

    print("\n  ✅ PASSED: First SQUASH request returns envelope with dict")
    return True


def test_3_cached_dict_request() -> bool:
    """Scenario 3: Client with current dict → envelope without __dict."""
    print_header("Test 3: Cached Dict → Envelope Without Dict")

    # Get the cached dict ID from the engine
    dict_id = engine.dict_store.get_dict_id("api")
    if dict_id is None:
        # Run test 2 first to populate cache
        test_2_first_squash_request()
        dict_id = engine.dict_store.get_dict_id("api")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={
            "Accept-Encoding": "squash",
            "X-SQUASH-DictId": dict_id,
        },
    )
    data = response.json()

    assert "__meta" in data
    assert "__dict" not in data, "Dict should be omitted when client is current"
    assert "d" in data

    print_json("Envelope (no __dict)", data)

    decoded = engine.decode(data)
    assert decoded["name"] == "Ashwin Kumar"
    print_json("Decoded", decoded)

    print("\n  ✅ PASSED: Cached dict request omits __dict")
    return True


def test_4_dict_version_mismatch() -> bool:
    """Scenario 4: Client with stale dict → server sends updated dict."""
    print_header("Test 4: Stale Dict → Server Sends Updated Dict")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={
            "Accept-Encoding": "squash",
            "X-SQUASH-DictId": "api_v0",  # Stale version
        },
    )
    data = response.json()

    assert "__meta" in data
    assert "__dict" in data, "Server must include __dict on version mismatch"

    print_json("Envelope (with updated __dict)", data)

    decoded = engine.decode(data)
    assert decoded["name"] == "Ashwin Kumar"

    print("\n  ✅ PASSED: Stale dict triggers dict refresh")
    return True


def test_5_nested_payload() -> bool:
    """Scenario 5: Verify nested payload compaction/expansion."""
    print_header("Test 5: Nested Payload Compaction")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={"Accept-Encoding": "squash"},
    )
    data = response.json()

    # Decode and verify nested structure
    decoded = engine.decode(data)

    assert "address" in decoded, "Decoded must have 'address' nested object"
    assert decoded["address"]["city"] == "Mumbai"
    assert decoded["address"]["zip_code"] == "400001"

    print_json("Original (decoded)", decoded)

    # Check compression
    original_size = len(json.dumps(decoded))
    compact_size = len(json.dumps(data))
    ratio = compact_size / original_size
    print(f"\n  Original size: {original_size} bytes")
    print(f"  Compact size:  {compact_size} bytes")
    print(f"  Ratio:         {ratio:.2%}")

    print("\n  ✅ PASSED: Nested payload round-trips correctly")
    return True


def test_6_list_endpoint() -> bool:
    """Scenario 6: Verify list endpoint compaction."""
    print_header("Test 6: List Endpoint")

    response = requests.get(
        f"{BASE_URL}/products",
        headers={"Accept-Encoding": "squash"},
    )
    data = response.json()

    assert "__meta" in data
    decoded = engine.decode(data)

    assert isinstance(decoded, list), "Products should be a list"
    assert len(decoded) == 2
    assert decoded[0]["name"] == "Kotlin in Action"

    print(f"\n  Products decoded: {len(decoded)}")
    for p in decoded:
        print(f"    - {p['name']} (₹{p['price']})")

    print("\n  ✅ PASSED: List endpoint works correctly")
    return True


def test_7_binary_request() -> bool:
    """Scenario 7: First SQUASH v2 Binary Request."""
    print_header("Test 7: First SQUASH v2 Binary Request")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={"Accept": "application/squash+proto"},
    )
    data = response.content

    assert response.headers.get("content-type") == "application/squash+proto"
    
    decoded = binary_engine.from_binary_frame(data)
    assert decoded.data["name"] == "Ashwin Kumar"
    
    print(f"\n  ✅ PASSED: Binary decoded correctly (size: {len(data)} bytes)")
    print(f"  Dict ID: {decoded.dict_id}")
    return True

def test_8_cached_binary_request() -> bool:
    """Scenario 8: Cached SQUASH v2 Binary Request."""
    print_header("Test 8: Cached SQUASH v2 Binary Request")
    
    dict_id = binary_engine.get_dict_id("api")

    response = requests.get(
        f"{BASE_URL}/users/1",
        headers={
            "Accept": "application/squash+proto",
            "X-SQUASH-DictId": dict_id,
        },
    )
    data = response.content

    assert response.headers.get("content-type") == "application/squash+proto"
    
    decoded = binary_engine.from_binary_frame(data)
    assert decoded.data["name"] == "Ashwin Kumar"
    
    print(f"\n  ✅ PASSED: Cached Binary decoded correctly (size: {len(data)} bytes)")
    return True


def test_9_complex_json_v1() -> bool:
    """Scenario 9: Verify complex JSON with nulls and arrays (v1)."""
    print_header("Test 9: Complex JSON (v1 JSON)")

    response = requests.get(
        f"{BASE_URL}/complex",
        headers={"Accept-Encoding": "squash"},
    )
    data = response.json()
    decoded = engine.decode(data)

    assert decoded["uuid"] == "123e4567-e89b-12d3-a456-426614174000"
    assert decoded["flags"] == [True, False, True, True]
    assert decoded["notes"] is None
    
    print("\n  ✅ PASSED: Complex JSON handled correctly in v1")
    return True


def test_10_complex_json_v2() -> bool:
    """Scenario 10: Verify complex JSON with nulls and arrays (v2 Binary)."""
    print_header("Test 10: Complex JSON (v2 Binary)")

    response = requests.get(
        f"{BASE_URL}/complex",
        headers={"Accept": "application/squash+proto"},
    )
    data = response.content
    decoded = binary_engine.from_binary_frame(data)

    assert decoded.data["uuid"] == "123e4567-e89b-12d3-a456-426614174000"
    assert decoded.data["flags"] == [True, False, True, True]
    
    print("\n  ✅ PASSED: Complex JSON handled correctly in v2 Binary")
    return True


def main() -> None:
    print("\n" + "🔬 SQUASH End-to-End Protocol Test Suite".center(60))
    print("=" * 60)

    tests = [
        test_1_non_squash_request,
        test_2_first_squash_request,
        test_3_cached_dict_request,
        test_4_dict_version_mismatch,
        test_5_nested_payload,
        test_6_list_endpoint,
        test_7_binary_request,
        test_8_cached_binary_request,
        test_9_complex_json_v1,
        test_10_complex_json_v2,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
