"""
SQUASH v2 — Binary Protocol Engine

Provides Protobuf-style binary wire format encoding for SQUASH,
achieving ~80% size reduction over raw JSON on repeated requests.
"""

from squash.v2.varint import Varint
from squash.v2.wire import BinaryWriter, BinaryReader, WireFormat
from squash.v2.binary_dictionary import BinaryDictionary, FieldType
from squash.v2.key_mapper import VarintKeyMapper
from squash.v2.binary_engine import BinarySquashEngine

__all__ = [
    "Varint",
    "BinaryWriter",
    "BinaryReader",
    "WireFormat",
    "BinaryDictionary",
    "FieldType",
    "VarintKeyMapper",
    "BinarySquashEngine",
]
