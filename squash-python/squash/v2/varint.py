"""
Unsigned Varint (LEB128) encoder/decoder for SQUASH v2.

Each byte uses 7 bits for data and 1 bit (MSB) as a continuation flag.
This is the same encoding used by Protocol Buffers.

Size characteristics:
    Values 0–127:       1 byte
    Values 128–16383:   2 bytes
    Values 16384–2097151: 3 bytes

Critical for SQUASH v2: Protobuf field tags for fields 1–15 encode as
single-byte Varints, making the most common fields extremely compact.
"""

from __future__ import annotations


class Varint:
    """LEB128 unsigned Varint codec."""

    @staticmethod
    def encode_zigzag(value: int) -> int:
        """ZigZag encode a signed integer into an unsigned integer."""
        return (value << 1) ^ (value >> 63)

    @staticmethod
    def decode_zigzag(value: int) -> int:
        """ZigZag decode an unsigned integer back to a signed integer."""
        return (value >> 1) ^ -(value & 1)

    @staticmethod
    def encode(value: int) -> bytes:
        """
        Encode an unsigned integer as a Varint byte sequence.

        Args:
            value: Non-negative integer to encode.

        Returns:
            bytes containing the Varint encoding.

        Raises:
            ValueError: If value is negative.
        """
        if value < 0:
            raise ValueError(f"Varint value must be non-negative, got {value}")

        result = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result.append(byte)
            if value == 0:
                break

        return bytes(result)

    @staticmethod
    def decode(data: bytes | bytearray, offset: int = 0) -> tuple[int, int]:
        """
        Decode a Varint from a byte sequence.

        Args:
            data: Byte sequence to read from.
            offset: Starting position in the sequence.

        Returns:
            Tuple of (decoded_value, bytes_consumed).

        Raises:
            ValueError: If the varint is malformed or truncated.
        """
        result = 0
        shift = 0
        pos = offset

        while pos < len(data):
            byte = data[pos]
            result |= (byte & 0x7F) << shift
            pos += 1

            if byte & 0x80 == 0:
                return result, pos - offset

            shift += 7
            if shift >= 64:
                raise ValueError("Varint too long (more than 10 bytes)")

        raise ValueError(f"Unexpected end of varint at offset {offset}")

    @staticmethod
    def encode_tag(field_number: int, wire_type: int) -> bytes:
        """
        Encode a Protobuf field tag (field_number << 3 | wire_type).

        Args:
            field_number: 1-based field number.
            wire_type: Wire type constant (0, 1, 2, or 5).

        Returns:
            Varint-encoded tag bytes.
        """
        tag = (field_number << 3) | wire_type
        return Varint.encode(tag)
