"""
Protobuf wire format utilities for SQUASH v2.

Provides BinaryWriter and BinaryReader for encoding/decoding
Protobuf-compatible wire format data, plus WireFormat constants.
"""

from __future__ import annotations

import struct
from typing import Any

from squash.v2.varint import Varint


class WireFormat:
    """Protobuf wire type constants and tag utilities."""

    WIRE_TYPE_VARINT = 0            # Variable-length integers
    WIRE_TYPE_FIXED64 = 1           # 8-byte values (double)
    WIRE_TYPE_LENGTH_DELIMITED = 2  # Strings, bytes, embedded messages
    WIRE_TYPE_FIXED32 = 5           # 4-byte values (float)

    @staticmethod
    def make_tag(field_number: int, wire_type: int) -> int:
        """Encode a field tag from field number and wire type."""
        return (field_number << 3) | wire_type

    @staticmethod
    def field_number(tag: int) -> int:
        """Extract field number from a tag."""
        return tag >> 3

    @staticmethod
    def wire_type(tag: int) -> int:
        """Extract wire type from a tag."""
        return tag & 0x07


class BinaryWriter:
    """
    Binary frame writer producing Protobuf-compatible wire format.

    Usage::

        writer = BinaryWriter()
        writer.write_string(1, "Ashwin")
        writer.write_int64(2, 28)
        writer.write_bool(3, True)
        data = writer.to_bytes()
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def write_string(self, field_number: int, value: str) -> None:
        """Write a tagged string field."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
        encoded = value.encode("utf-8")
        self._buffer.extend(Varint.encode(len(encoded)))
        self._buffer.extend(encoded)

    def write_int64(self, field_number: int, value: int) -> None:
        """Write a tagged int64 (varint) field."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_VARINT)
        self._buffer.extend(Varint.encode(value))

    def write_sint64(self, field_number: int, value: int) -> None:
        """Write a tagged signed int64 (zigzag varint) field."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_VARINT)
        self._buffer.extend(Varint.encode(Varint.encode_zigzag(value)))

    def write_bool(self, field_number: int, value: bool) -> None:
        """Write a tagged boolean field (varint 0 or 1)."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_VARINT)
        self._buffer.extend(Varint.encode(1 if value else 0))

    def write_double(self, field_number: int, value: float) -> None:
        """Write a tagged double field (fixed 64-bit, little-endian)."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_FIXED64)
        self._buffer.extend(struct.pack("<d", value))

    def write_float(self, field_number: int, value: float) -> None:
        """Write a tagged float field (fixed 32-bit, little-endian)."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_FIXED32)
        self._buffer.extend(struct.pack("<f", value))

    def write_bytes(self, field_number: int, value: bytes) -> None:
        """Write a tagged bytes field (length-delimited)."""
        self._write_tag(field_number, WireFormat.WIRE_TYPE_LENGTH_DELIMITED)
        self._buffer.extend(Varint.encode(len(value)))
        self._buffer.extend(value)

    def write_embedded(self, field_number: int, embedded: bytes) -> None:
        """Write a tagged embedded message field."""
        self.write_bytes(field_number, embedded)

    def _write_tag(self, field_number: int, wire_type: int) -> None:
        tag = WireFormat.make_tag(field_number, wire_type)
        self._buffer.extend(Varint.encode(tag))

    def to_bytes(self) -> bytes:
        """Return the accumulated buffer as bytes."""
        return bytes(self._buffer)

    @property
    def size(self) -> int:
        """Current buffer size in bytes."""
        return len(self._buffer)

    def reset(self) -> None:
        """Reset the writer for reuse."""
        self._buffer.clear()


class BinaryReader:
    """
    Streaming binary frame reader for Protobuf-compatible wire format.

    Usage::

        reader = BinaryReader(data)
        while not reader.is_at_end():
            tag = reader.read_tag()
            fn = WireFormat.field_number(tag)
            wt = WireFormat.wire_type(tag)
            if wt == WireFormat.WIRE_TYPE_LENGTH_DELIMITED:
                value = reader.read_string()
    """

    def __init__(self, data: bytes | bytearray) -> None:
        self._data = data
        self._pos = 0

    def is_at_end(self) -> bool:
        """True if there are no more bytes to read."""
        return self._pos >= len(self._data)

    @property
    def position(self) -> int:
        """Current read position."""
        return self._pos

    @property
    def remaining(self) -> int:
        """Number of remaining bytes."""
        return len(self._data) - self._pos

    def read_tag(self) -> int:
        """Read a field tag (varint). Returns 0 at end of stream."""
        if self.is_at_end():
            return 0
        return self.read_varint()

    def read_varint(self) -> int:
        """Read a varint value."""
        value, consumed = Varint.decode(self._data, self._pos)
        self._pos += consumed
        return value

    def read_string(self) -> str:
        """Read a length-delimited string."""
        length = self.read_varint()
        if self._pos + length > len(self._data):
            raise ValueError(
                f"String length {length} exceeds available data at position {self._pos}"
            )
        s = self._data[self._pos : self._pos + length].decode("utf-8")
        self._pos += length
        return s

    def read_bytes(self) -> bytes:
        """Read a length-delimited byte array."""
        length = self.read_varint()
        if self._pos + length > len(self._data):
            raise ValueError(
                f"Bytes length {length} exceeds available data at position {self._pos}"
            )
        b = self._data[self._pos : self._pos + length]
        self._pos += length
        return bytes(b)

    def read_sint64(self) -> int:
        """Read a zigzag-encoded signed varint from the stream."""
        val = self.read_varint()
        return Varint.decode_zigzag(val)

    def read_bool(self) -> bool:
        """Read a boolean (varint 0 or 1)."""
        return self.read_varint() != 0

    def read_double(self) -> float:
        """Read a double (fixed 64-bit, little-endian)."""
        if self._pos + 8 > len(self._data):
            raise ValueError(f"Not enough data for double at position {self._pos}")
        value = struct.unpack_from("<d", self._data, self._pos)[0]
        self._pos += 8
        return value

    def read_float(self) -> float:
        """Read a float (fixed 32-bit, little-endian)."""
        if self._pos + 4 > len(self._data):
            raise ValueError(f"Not enough data for float at position {self._pos}")
        value = struct.unpack_from("<f", self._data, self._pos)[0]
        self._pos += 4
        return value

    def skip_field(self, wire_type: int) -> None:
        """Skip a field value based on its wire type."""
        if wire_type == WireFormat.WIRE_TYPE_VARINT:
            self.read_varint()
        elif wire_type == WireFormat.WIRE_TYPE_FIXED64:
            if self._pos + 8 > len(self._data):
                raise ValueError("Not enough data to skip fixed64")
            self._pos += 8
        elif wire_type == WireFormat.WIRE_TYPE_LENGTH_DELIMITED:
            length = self.read_varint()
            if self._pos + length > len(self._data):
                raise ValueError("Not enough data to skip length-delimited")
            self._pos += length
        elif wire_type == WireFormat.WIRE_TYPE_FIXED32:
            if self._pos + 4 > len(self._data):
                raise ValueError("Not enough data to skip fixed32")
            self._pos += 4
        else:
            raise ValueError(f"Unknown wire type: {wire_type}")
