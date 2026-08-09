"""
SQUASH v2 Binary Dictionary and FieldType enum.

Maps dense integer field tags (1-based) to canonical JSON key paths,
with optional type hints for binary deserialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property
from typing import Any


class FieldType(IntEnum):
    """Type hints for binary field deserialization."""

    UNSPECIFIED = 0
    STRING = 1      # Wire type 2 (length-delimited)
    INT64 = 2       # Wire type 0 (varint)
    DOUBLE = 3      # Wire type 1 (fixed 64-bit)
    BOOL = 4        # Wire type 0 (varint)
    BYTES = 5       # Wire type 2 (length-delimited)
    EMBEDDED = 6    # Wire type 2 (nested SQUASH object)


class EncodingType(IntEnum):
    """SQUASH v2 encoding modes."""

    UNSPECIFIED = 0
    BINARY_MAP = 1        # Field Tag (Varint) → Encoded Value
    BINARY_ARRAY = 2      # Ordered Packed Values (future)
    PROTOBUF_DYNAMIC = 3  # Full Protobuf dynamic mapping (future)


@dataclass
class BinaryDictionary:
    """
    SQUASH v2 dictionary with integer field tags and type hints.

    Field tags 1–15 encode as single-byte Varints, making the most common
    fields extremely space-efficient.

    Attributes:
        dict_id: Unique identifier in ``{schema}_v{version}`` format.
        version: Monotonically increasing version.
        field_mappings: Field tag (1-based int) → canonical JSON key path.
        type_hints: Field tag → FieldType for binary deserialization.
    """

    dict_id: str
    version: int
    field_mappings: dict[int, str]
    type_hints: dict[int, FieldType] = field(default_factory=dict)
    value_dictionary: list[str] = field(default_factory=list)

    @cached_property
    def reverse_mappings(self) -> dict[str, int]:
        """JSON key path → field tag. Used during encoding."""
        return {v: k for k, v in self.field_mappings.items()}

    @cached_property
    def reverse_value_dictionary(self) -> dict[str, int]:
        """String value → index. Used for string interning during encoding."""
        return {v: k for k, v in enumerate(self.value_dictionary)}

    @property
    def schema_name(self) -> str:
        """Schema name from dictId (e.g., 'user' from 'user_v1')."""
        return self.dict_id.rsplit("_v", 1)[0]

    @property
    def field_count(self) -> int:
        """Number of fields in this dictionary."""
        return len(self.field_mappings)

    def type_for(self, field_tag: int) -> FieldType:
        """Returns the type hint for a field, defaulting to STRING."""
        return self.type_hints.get(field_tag, FieldType.STRING)
