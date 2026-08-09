"""Tests for KeyCompactor and JsonTransformer."""

from squash.compactor import JsonTransformer, KeyCompactor


class TestKeyCompactor:
    """Test key path extraction and mapping."""

    def test_flat_object(self):
        data = {"name": "Ashwin", "email": "a@b.com"}
        paths = KeyCompactor.extract_key_paths(data)
        assert paths == ["name", "email"]

    def test_nested_object(self):
        data = {"user": {"name": "Ashwin", "address": {"city": "Mumbai", "zip": "400001"}}}
        paths = KeyCompactor.extract_key_paths(data)
        assert paths == ["user.name", "user.address.city", "user.address.zip"]

    def test_array_of_objects(self):
        data = {"users": [{"name": "Ashwin", "age": 28}, {"name": "Ravi", "age": 30}]}
        paths = KeyCompactor.extract_key_paths(data)
        assert paths == ["users.name", "users.age"]

    def test_array_of_primitives(self):
        data = {"tags": ["kotlin", "java"], "name": "lib"}
        paths = KeyCompactor.extract_key_paths(data)
        assert paths == ["tags", "name"]

    def test_build_mapping(self):
        paths = ["name", "email", "address.city"]
        mapping = KeyCompactor.build_mapping(paths)
        assert mapping == {"a": "name", "b": "email", "c": "address.city"}

    def test_empty_object(self):
        assert KeyCompactor.extract_key_paths({}) == []

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": "value"}}}}
        paths = KeyCompactor.extract_key_paths(data)
        assert paths == ["a.b.c.d"]


class TestJsonTransformerCompact:
    """Test JSON compaction."""

    def test_flat_object(self):
        data = {"name": "Ashwin", "email": "a@b.com"}
        reverse = {"name": "a", "email": "b"}
        result = JsonTransformer.compact(data, reverse)
        assert result == {"a": "Ashwin", "b": "a@b.com"}

    def test_nested_object(self):
        data = {"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}}
        reverse = {"user.name": "a", "user.address.city": "b"}
        result = JsonTransformer.compact(data, reverse)
        assert result == {"a": "Ashwin", "b": "Mumbai"}

    def test_preserves_primitives(self):
        data = {"count": 42, "active": True, "name": "test"}
        reverse = {"count": "a", "active": "b", "name": "c"}
        result = JsonTransformer.compact(data, reverse)
        assert result == {"a": 42, "b": True, "c": "test"}


class TestJsonTransformerExpand:
    """Test JSON expansion."""

    def test_flat_expand(self):
        compacted = {"a": "Ashwin", "b": "a@b.com"}
        mapping = {"a": "name", "b": "email"}
        result = JsonTransformer.expand(compacted, mapping)
        assert result == {"name": "Ashwin", "email": "a@b.com"}

    def test_nested_expand(self):
        compacted = {"a": "Ashwin", "b": "Mumbai"}
        mapping = {"a": "user.name", "b": "user.address.city"}
        result = JsonTransformer.expand(compacted, mapping)
        assert result == {"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}}

    def test_unknown_keys_pass_through(self):
        compacted = {"a": "value", "unknown": "other"}
        mapping = {"a": "name"}
        result = JsonTransformer.expand(compacted, mapping)
        assert result == {"name": "value", "unknown": "other"}


class TestJsonTransformerRoundTrip:
    """Test compact → expand round-trips."""

    def test_flat_roundtrip(self):
        original = {"name": "Ashwin", "email": "a@b.com", "age": 28}
        reverse = {"name": "a", "email": "b", "age": "c"}
        mapping = {v: k for k, v in reverse.items()}

        compacted = JsonTransformer.compact(original, reverse)
        expanded = JsonTransformer.expand(compacted, mapping)
        assert expanded == original

    def test_nested_roundtrip(self):
        original = {
            "user": {
                "name": "Ashwin",
                "address": {"city": "Mumbai", "zip": "400001"},
            }
        }
        reverse = {
            "user.name": "a",
            "user.address.city": "b",
            "user.address.zip": "c",
        }
        mapping = {v: k for k, v in reverse.items()}

        compacted = JsonTransformer.compact(original, reverse)
        expanded = JsonTransformer.expand(compacted, mapping)
        assert expanded == original
