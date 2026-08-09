"""
Varint Key Mapper — translates SQUASH v1 Base62 dictionaries
into v2 dense integer field tag dictionaries.

Assigns 1-based sequential tags preserving v1 key order:
    v1: { "a" → "user.name", "b" → "user.email" }
    v2: { 1 → "user.name", 2 → "user.email" }
"""

from __future__ import annotations

from typing import Any

from squash.v2.binary_dictionary import BinaryDictionary, FieldType


class VarintKeyMapper:
    """Converts v1 Base62 dictionaries to v2 integer-tagged dictionaries."""

    @staticmethod
    def from_v1_dictionary(
        v1_mapping: dict[str, str],
        dict_id: str,
        version: int,
        sample_data: Any = None,
    ) -> BinaryDictionary:
        """
        Convert a v1 dictionary mapping to a v2 BinaryDictionary.

        Args:
            v1_mapping: Base62 short key → original key path.
            dict_id: Dictionary identifier.
            version: Dictionary version.
            sample_data: Optional sample JSON for type inference.

        Returns:
            A BinaryDictionary with 1-based integer field tags.
        """
        sorted_entries = sorted(v1_mapping.items(), key=lambda x: x[0])

        field_mappings: dict[int, str] = {}
        type_hints: dict[int, FieldType] = {}

        for index, (_, key_path) in enumerate(sorted_entries):
            field_tag = index + 1  # 1-based
            field_mappings[field_tag] = key_path

            if sample_data is not None:
                type_hints[field_tag] = VarintKeyMapper.infer_field_type(
                    sample_data, key_path
                )

        value_dictionary: list[str] = []
        if sample_data is not None:
            value_dictionary = VarintKeyMapper._extract_string_values(sample_data)

        return BinaryDictionary(
            dict_id=dict_id,
            version=version,
            field_mappings=field_mappings,
            type_hints=type_hints,
            value_dictionary=value_dictionary,
        )

    @staticmethod
    def build_dictionary(
        schema_name: str,
        version: int,
        key_paths: list[str],
        sample_data: Any = None,
    ) -> BinaryDictionary:
        """
        Build a v2 dictionary directly from key paths.

        Args:
            schema_name: Schema name (e.g., "user").
            version: Version number.
            key_paths: Ordered list of dot-notation key paths.
            sample_data: Optional sample data for type inference.

        Returns:
            A BinaryDictionary.
        """
        field_mappings: dict[int, str] = {}
        type_hints: dict[int, FieldType] = {}

        for index, key_path in enumerate(key_paths):
            field_tag = index + 1
            field_mappings[field_tag] = key_path

            if sample_data is not None:
                type_hints[field_tag] = VarintKeyMapper.infer_field_type(
                    sample_data, key_path
                )

        value_dictionary: list[str] = []
        if sample_data is not None:
            value_dictionary = VarintKeyMapper._extract_string_values(sample_data)

        return BinaryDictionary(
            dict_id=f"{schema_name}_v{version}",
            version=version,
            field_mappings=field_mappings,
            type_hints=type_hints,
            value_dictionary=value_dictionary,
        )

    @staticmethod
    def extract_paths(data: Any, prefix: str = "") -> list[str]:
        """Extract dot-notation key paths from data, stopping at nested lists."""
        paths = []
        if isinstance(data, dict):
            for k, v in data.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    paths.extend(VarintKeyMapper.extract_paths(v, p))
                else:
                    paths.append(p)
        elif isinstance(data, list) and prefix == "":
            for item in data:
                paths.extend(VarintKeyMapper.extract_paths(item, prefix))
        return paths

    @staticmethod
    def _extract_string_values(data: Any, max_strings: int = 127) -> list[str]:
        """Extract unique string values from sample data up to a limit."""
        strings: dict[str, bool] = {}
        
        def walk(node: Any) -> None:
            if len(strings) >= max_strings:
                return
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str):
                if node not in strings:
                    strings[node] = True

        walk(data)
        return list(strings.keys())

    @staticmethod
    def infer_field_type(data: Any, key_path: str) -> FieldType:
        """
        Infer the FieldType of a value at a dot-notation path.

        Args:
            data: JSON-like Python value.
            key_path: Dot-notation path to resolve.

        Returns:
            Inferred FieldType.
        """
        value = VarintKeyMapper._resolve_path(data, key_path)
        if value is None:
            return FieldType.STRING

        if isinstance(value, bool):
            return FieldType.BOOL
        if isinstance(value, int):
            return FieldType.INT64
        if isinstance(value, float):
            return FieldType.DOUBLE
        if isinstance(value, str):
            return FieldType.STRING
        if isinstance(value, (dict, list)):
            return FieldType.EMBEDDED
        if isinstance(value, bytes):
            return FieldType.BYTES

        return FieldType.STRING

    @staticmethod
    def _resolve_path(data: Any, path: str) -> Any:
        """Resolve a dot-notation path in a JSON-like structure."""
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            elif isinstance(current, list):
                first_obj = next(
                    (item for item in current if isinstance(item, dict)), None
                )
                if first_obj is not None:
                    current = first_obj.get(part)
                else:
                    return None
            else:
                return None

        return current
