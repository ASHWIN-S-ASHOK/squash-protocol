"""Tests for the SquashEngine."""

import pytest

from squash.dictionary import DictionaryBuilder
from squash.engine import SquashEngine


class TestSquashEngineEncode:
    """Test encoding operations."""

    def test_creates_valid_envelope(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}
        envelope = engine.encode(original, "user")

        assert envelope["__meta"]["v"] == 1
        assert envelope["__meta"]["dictId"] == "user_v1"
        assert envelope["__meta"]["encoding"] == "map"
        assert "__dict" in envelope  # First encode includes dict
        assert "d" in envelope

    def test_omits_dict_when_current(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}
        engine.encode(original, "user")  # Build and cache dict

        envelope = engine.encode(original, "user", client_dict_id="user_v1")
        assert "__dict" not in envelope

    def test_includes_dict_on_mismatch(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}
        engine.encode(original, "user")

        envelope = engine.encode(original, "user", client_dict_id="user_v0")
        assert "__dict" in envelope


class TestSquashEngineDecode:
    """Test decoding operations."""

    def test_decode_with_embedded_dict(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}
        envelope = engine.encode(original, "user")
        decoded = engine.decode(envelope)

        assert decoded["name"] == "Ashwin"
        assert decoded["email"] == "a@b.com"

    def test_decode_with_cached_dict(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}

        # First encode caches the dict
        envelope1 = engine.encode(original, "user")
        engine.decode(envelope1)

        # Second encode without dict
        envelope2 = engine.encode(original, "user", client_dict_id="user_v1")
        assert "__dict" not in envelope2

        decoded = engine.decode(envelope2)
        assert decoded["name"] == "Ashwin"

    def test_decode_without_dict_or_cache_raises(self):
        engine1 = SquashEngine()
        original = {"name": "Ashwin"}
        envelope = engine1.encode(original, "user", client_dict_id="user_v1")

        engine2 = SquashEngine()
        with pytest.raises(ValueError, match="No dictionary found"):
            engine2.decode(envelope)


class TestSquashEngineRoundTrip:
    """Test full encode → decode round-trips."""

    def test_flat_roundtrip(self):
        engine = SquashEngine()
        original = {"name": "Ashwin", "email": "a@b.com"}
        envelope = engine.encode(original, "user")
        decoded = engine.decode(envelope)
        assert decoded == original

    def test_nested_roundtrip(self):
        engine = SquashEngine()
        original = {
            "user": {
                "name": "Ashwin",
                "address": {"city": "Mumbai", "zip": "400001"},
            }
        }
        envelope = engine.encode(original, "profile")
        decoded = engine.decode(envelope)
        assert decoded == original

    def test_should_include_dict_logic(self):
        engine = SquashEngine()
        assert engine.should_include_dict("user_v1", None) is True
        assert engine.should_include_dict("user_v2", "user_v1") is True
        assert engine.should_include_dict("user_v1", "user_v1") is False

    def test_register_dictionary(self):
        engine = SquashEngine()
        d = DictionaryBuilder.build_from_paths("custom", 1, ["field1", "field2"])
        engine.register_dictionary(d)

        assert engine.dict_store.get("custom") is not None
        assert engine.dict_store.get_dict_id("custom") == "custom_v1"
