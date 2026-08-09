"""
Base62 key generator for SQUASH dictionary encoding.

Generates deterministic short keys in the following order:
    0  → "a"   ...  25 → "z"
    26 → "A"   ...  51 → "Z"
    52 → "0"   ...  61 → "9"
    62 → "aa"  ...  63 → "ab"  ...  123 → "ba"  ...

This mirrors the Kotlin implementation exactly to ensure cross-platform
dictionary compatibility.
"""

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
BASE = 62


class Base62:
    """Base62 key encoder for SQUASH short key generation."""

    @staticmethod
    def encode(index: int) -> str:
        """
        Convert a zero-based index to a Base62 short key.

        Args:
            index: Zero-based index (0, 1, 2, …).

        Returns:
            The Base62 encoded short key string.

        Raises:
            ValueError: If index is negative.
        """
        if index < 0:
            raise ValueError(f"Index must be non-negative, got {index}")

        if index < BASE:
            return ALPHABET[index]

        # Multi-character keys for indices >= 62
        remaining = index - BASE
        chars: list[str] = []

        while True:
            chars.insert(0, ALPHABET[remaining % BASE])
            remaining //= BASE
            if remaining <= 0:
                break

        # Ensure minimum 2 characters
        while len(chars) < 2:
            chars.insert(0, ALPHABET[0])

        return "".join(chars)

    @staticmethod
    def generate_keys(count: int) -> list[str]:
        """
        Generate a list of sequential Base62 keys starting from index 0.

        Args:
            count: Number of keys to generate.

        Returns:
            List of Base62 keys: ["a", "b", …, "z", "A", …, "Z", "0", …, "9", "aa", …]

        Raises:
            ValueError: If count is negative.
        """
        if count < 0:
            raise ValueError(f"Count must be non-negative, got {count}")
        return [Base62.encode(i) for i in range(count)]
