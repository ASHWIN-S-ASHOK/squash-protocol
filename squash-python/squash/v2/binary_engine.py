"""
SQUASH v2 Binary Protocol Engine.

Encodes JSON payloads into compact binary frames using Protobuf wire format
with Varint-indexed field tags, and decodes them back.

Binary Frame Structure:
    [Tag 1: version (varint)]
    [Tag 2: dictId (string)]
    [Tag 3: encoding (varint)]
    [Tag 4: dict data (bytes, optional)]
    [Tag 5: payload (bytes)]
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from squash.compactor import KeyCompactor
from squash.v2.binary_dictionary import BinaryDictionary, EncodingType, FieldType
from squash.v2.key_mapper import VarintKeyMapper
from squash.v2.varint import Varint
from squash.v2.wire import BinaryReader, BinaryWriter, WireFormat

# Frame-level field numbers
FRAME_VERSION = 1
FRAME_DICT_ID = 2
FRAME_ENCODING = 3
FRAME_DICT_DATA = 4
FRAME_PAYLOAD = 5


@dataclass
class DecompactResult:
    """Result of decoding a binary frame."""

    data: Any
    dict_id: str
    version: int
    encoding: EncodingType


class BinarySquashEngine:
    """
    SQUASH v2 Binary Protocol Engine.

    Encodes JSON payloads into compact binary frames and decodes them back.
    Manages a dictionary store for caching v2 dictionaries.
    """

    def __init__(self) -> None:
        self._dict_store: dict[str, BinaryDictionary] = {}

    def to_binary_frame(
        self,
        original: Any,
        schema_name: str,
        client_dict_id: str | None = None,
    ) -> bytes:
        """
        Encode a JSON-like value into a compact binary frame.

        Args:
            original: The original JSON data.
            schema_name: Schema name for dictionary lookup/creation.
            client_dict_id: Client's cached dictId for sync logic.

        Returns:
            Binary frame as bytes.
        """
        # Get or build v2 dictionary
        dictionary = self._dict_store.get(schema_name)
        if dictionary is None:
            key_paths = VarintKeyMapper.extract_paths(original)
            dictionary = VarintKeyMapper.build_dictionary(
                schema_name, 1, key_paths, original
            )
            self._dict_store[schema_name] = dictionary

        # Encode payload
        if isinstance(original, list):
            encoding = EncodingType.BINARY_ARRAY
            payload_buffer = bytearray()
            for item in original:
                item_bytes = self.encode_payload(item, dictionary)
                payload_buffer.extend(Varint.encode(len(item_bytes)))
                payload_buffer.extend(item_bytes)
            payload_bytes = bytes(payload_buffer)
        else:
            encoding = EncodingType.BINARY_MAP
            payload_bytes = self.encode_payload(original, dictionary)

        # Dict sync
        include_dict = self.should_include_dict(dictionary.dict_id, client_dict_id)

        # Write frame
        writer = BinaryWriter()
        writer.write_int64(FRAME_VERSION, 2)
        writer.write_string(FRAME_DICT_ID, dictionary.dict_id)
        writer.write_int64(FRAME_ENCODING, encoding)

        if include_dict:
            dict_bytes = self._serialize_dictionary(dictionary)
            writer.write_bytes(FRAME_DICT_DATA, dict_bytes)

        writer.write_bytes(FRAME_PAYLOAD, payload_bytes)

        return writer.to_bytes()

    def from_binary_frame(self, frame_bytes: bytes) -> DecompactResult:
        """
        Decode a binary frame back into the original JSON structure.

        Args:
            frame_bytes: The binary frame bytes.

        Returns:
            DecompactResult with the expanded data and metadata.
        """
        reader = BinaryReader(frame_bytes)

        version = 2
        dict_id = ""
        encoding = EncodingType.BINARY_MAP
        dict_bytes: bytes | None = None
        payload_bytes: bytes | None = None

        while not reader.is_at_end():
            tag = reader.read_tag()
            if tag == 0:
                break
            fn = WireFormat.field_number(tag)
            wt = WireFormat.wire_type(tag)

            if fn == FRAME_VERSION:
                version = reader.read_varint()
            elif fn == FRAME_DICT_ID:
                dict_id = reader.read_string()
            elif fn == FRAME_ENCODING:
                encoding = EncodingType(reader.read_varint())
            elif fn == FRAME_DICT_DATA:
                dict_bytes = reader.read_bytes()
            elif fn == FRAME_PAYLOAD:
                payload_bytes = reader.read_bytes()
            else:
                reader.skip_field(wt)

        if payload_bytes is None:
            raise ValueError("Binary frame has no payload (field 5)")
        if not dict_id:
            raise ValueError("Binary frame has no dictId (field 2)")

        # Resolve dictionary
        if dict_bytes is not None:
            dictionary = self._deserialize_dictionary(dict_bytes, dict_id)
            self._dict_store[dictionary.schema_name] = dictionary
        else:
            schema_name = dict_id.rsplit("_v", 1)[0]
            dictionary = self._dict_store.get(schema_name)
            if dictionary is None or dictionary.dict_id != dict_id:
                raise ValueError(
                    f"No dictionary found for dictId '{dict_id}'. "
                    "The server should have included dict data in the frame."
                )

        # Decode payload based on encoding
        if encoding == EncodingType.BINARY_MAP:
            data = self.decode_payload(payload_bytes, dictionary)
        elif encoding == EncodingType.BINARY_ARRAY:
            data = []
            payload_reader = BinaryReader(payload_bytes)
            while not payload_reader.is_at_end():
                item_bytes = payload_reader.read_bytes()
                data.append(self.decode_payload(item_bytes, dictionary))
        else:
            raise ValueError(f"Unsupported encoding: {encoding}")

        return DecompactResult(
            data=data,
            dict_id=dict_id,
            version=version,
            encoding=encoding,
        )

    def encode_payload(self, data: Any, dictionary: BinaryDictionary) -> bytes:
        """Encode a JSON-like value as binary using the dictionary's field mappings."""
        writer = BinaryWriter()
        flat = self._flatten(data)

        for key_path, value in flat.items():
            field_tag = dictionary.reverse_mappings.get(key_path)
            if field_tag is None:
                continue
            field_type = dictionary.type_for(field_tag)
            self._write_field(writer, field_tag, value, field_type, dictionary)

        return writer.to_bytes()

    def decode_payload(
        self, payload_bytes: bytes, dictionary: BinaryDictionary
    ) -> Any:
        """Decode binary payload bytes into a nested dict."""
        reader = BinaryReader(payload_bytes)
        values: dict[str, Any] = {}

        while not reader.is_at_end():
            tag = reader.read_tag()
            if tag == 0:
                break
            fn = WireFormat.field_number(tag)
            wt = WireFormat.wire_type(tag)

            key_path = dictionary.field_mappings.get(fn)
            if key_path is None:
                reader.skip_field(wt)
                continue

            field_type = dictionary.type_for(fn)
            values[key_path] = self._read_field(reader, wt, field_type, dictionary)

        return self._unflatten(values)

    # ─── Field Writing ────────────────────────────────────────

    @staticmethod
    def _write_field(
        writer: BinaryWriter,
        field_tag: int,
        value: Any,
        field_type: FieldType,
        dictionary: BinaryDictionary,
    ) -> None:
        if value is None:
            return

        if isinstance(value, bool):
            writer.write_bool(field_tag, value)
        elif isinstance(value, int):
            writer.write_sint64(field_tag, value)
        elif isinstance(value, float):
            writer.write_double(field_tag, value)
        elif isinstance(value, str):
            index = dictionary.reverse_value_dictionary.get(value)
            if index is not None:
                writer.write_int64(field_tag, index)
            else:
                writer.write_string(field_tag, value)
        elif isinstance(value, (list, dict)):
            # Complex values — serialize as JSON string
            writer.write_string(field_tag, json.dumps(value, separators=(",", ":")))
        else:
            writer.write_string(field_tag, str(value))

    @staticmethod
    def _read_field(
        reader: BinaryReader,
        wire_type: int,
        field_type: FieldType,
        dictionary: BinaryDictionary,
    ) -> Any:
        if wire_type == WireFormat.WIRE_TYPE_VARINT:
            if field_type == FieldType.INT64:
                return reader.read_sint64()
            v = reader.read_varint()
            if field_type == FieldType.BOOL:
                return v != 0
            if field_type == FieldType.STRING:
                if 0 <= v < len(dictionary.value_dictionary):
                    return dictionary.value_dictionary[v]
                return ""
            # Fallback for old fields
            return v
        elif wire_type == WireFormat.WIRE_TYPE_FIXED64:
            return reader.read_double()
        elif wire_type == WireFormat.WIRE_TYPE_FIXED32:
            return reader.read_float()
        elif wire_type == WireFormat.WIRE_TYPE_LENGTH_DELIMITED:
            s = reader.read_string()
            if field_type == FieldType.EMBEDDED or (field_type == FieldType.STRING and s.startswith(("[", "{"))):
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, ValueError):
                    return s
            return s
        else:
            reader.skip_field(wire_type)
            return None

    # ─── Flatten / Unflatten ──────────────────────────────────

    @staticmethod
    def _flatten(data: Any, prefix: str = "") -> dict[str, Any]:
        """Flatten a nested dict to dot-notation keys."""
        result: dict[str, Any] = {}
        if isinstance(data, dict):
            for key, value in data.items():
                full_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    result.update(BinarySquashEngine._flatten(value, full_path))
                else:
                    result[full_path] = value
        else:
            if prefix:
                result[prefix] = data
        return result

    @staticmethod
    def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
        """Unflatten dot-notation keys to nested dict."""
        result: dict[str, Any] = {}
        for path, value in flat.items():
            parts = path.split(".")
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result

    # ─── Dictionary Serialization ─────────────────────────────

    @staticmethod
    def _serialize_dictionary(dictionary: BinaryDictionary) -> bytes:
        """Serialize a BinaryDictionary to binary format."""
        writer = BinaryWriter()
        for tag in sorted(dictionary.field_mappings.keys()):
            path = dictionary.field_mappings[tag]
            writer.write_int64(1, tag)
            writer.write_string(2, path)
            type_hint = dictionary.type_hints.get(tag, FieldType.STRING)
            writer.write_int64(3, int(type_hint))
        for value in dictionary.value_dictionary:
            writer.write_string(4, value)
        return writer.to_bytes()

    @staticmethod
    def _deserialize_dictionary(
        data: bytes, dict_id: str
    ) -> BinaryDictionary:
        """Deserialize a BinaryDictionary from binary format."""
        reader = BinaryReader(data)
        field_mappings: dict[int, str] = {}
        type_hints: dict[int, FieldType] = {}
        value_dictionary: list[str] = []

        current_tag = 0

        while not reader.is_at_end():
            tag = reader.read_tag()
            if tag == 0:
                break
            fn = WireFormat.field_number(tag)

            if fn == 1:
                current_tag = reader.read_varint()
            elif fn == 2:
                path = reader.read_string()
                field_mappings[current_tag] = path
            elif fn == 3:
                type_val = reader.read_varint()
                type_hints[current_tag] = FieldType(type_val)
            elif fn == 4:
                value_dictionary.append(reader.read_string())
            else:
                reader.skip_field(WireFormat.wire_type(tag))

        try:
            version = int(dict_id.rsplit("_v", 1)[1])
        except (IndexError, ValueError):
            version = 1

        return BinaryDictionary(
            dict_id=dict_id,
            version=version,
            field_mappings=field_mappings,
            type_hints=type_hints,
            value_dictionary=value_dictionary,
        )

    # ─── Dict Sync ────────────────────────────────────────────

    @staticmethod
    def should_include_dict(
        server_dict_id: str, client_dict_id: str | None
    ) -> bool:
        """Whether to include dict data in the frame."""
        if client_dict_id is None:
            return True
        return client_dict_id != server_dict_id

    def register_dictionary(self, dictionary: BinaryDictionary) -> None:
        """Register a pre-built dictionary."""
        self._dict_store[dictionary.schema_name] = dictionary

    def get_dict_id(self, schema_name: str) -> str | None:
        """Get the cached dictId for a schema."""
        d = self._dict_store.get(schema_name)
        return d.dict_id if d else None
