"""Tests for the Base62 encoder."""

import pytest

from squash.base62 import Base62


class TestBase62Encode:
    """Test Base62.encode() for all character ranges and edge cases."""

    def test_lowercase_range(self):
        assert Base62.encode(0) == "a"
        assert Base62.encode(1) == "b"
        assert Base62.encode(25) == "z"

    def test_uppercase_range(self):
        assert Base62.encode(26) == "A"
        assert Base62.encode(27) == "B"
        assert Base62.encode(51) == "Z"

    def test_digit_range(self):
        assert Base62.encode(52) == "0"
        assert Base62.encode(53) == "1"
        assert Base62.encode(61) == "9"

    def test_multi_char_starts_at_62(self):
        assert Base62.encode(62) == "aa"
        assert Base62.encode(63) == "ab"
        assert Base62.encode(87) == "az"
        assert Base62.encode(88) == "aA"
        assert Base62.encode(123) == "a9"

    def test_multi_char_second_group(self):
        assert Base62.encode(124) == "ba"
        assert Base62.encode(125) == "bb"

    def test_negative_index_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Base62.encode(-1)


class TestBase62GenerateKeys:
    """Test Base62.generate_keys() for correctness and uniqueness."""

    def test_generates_correct_count(self):
        keys = Base62.generate_keys(5)
        assert keys == ["a", "b", "c", "d", "e"]

    def test_generates_across_boundary(self):
        keys = Base62.generate_keys(64)
        assert keys[0] == "a"
        assert keys[61] == "9"
        assert keys[62] == "aa"
        assert keys[63] == "ab"

    def test_empty(self):
        assert Base62.generate_keys(0) == []

    def test_negative_count_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Base62.generate_keys(-1)

    def test_all_single_char_unique(self):
        keys = Base62.generate_keys(62)
        assert len(set(keys)) == 62

    def test_first_200_unique(self):
        keys = Base62.generate_keys(200)
        assert len(set(keys)) == 200


class TestBase62CrossPlatformParity:
    """
    Verify Python Base62 output matches the Kotlin implementation.
    These test vectors are shared between both platforms.
    """

    EXPECTED_KEYS = {
        0: "a", 1: "b", 25: "z",
        26: "A", 51: "Z",
        52: "0", 61: "9",
        62: "aa", 63: "ab", 123: "a9",
        124: "ba", 125: "bb",
    }

    @pytest.mark.parametrize("index,expected", EXPECTED_KEYS.items())
    def test_parity(self, index: int, expected: str):
        assert Base62.encode(index) == expected
