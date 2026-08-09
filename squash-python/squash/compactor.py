"""
Key compaction and JSON tree transformation for SQUASH.

KeyCompactor: Extracts leaf key paths and assigns Base62 short codes.
JsonTransformer: Bidirectional compact ↔ expand operations on JSON trees.
"""

from __future__ import annotations

from typing import Any

from squash.base62 import Base62


class KeyCompactor:
    """Extracts leaf key paths from JSON structures and builds Base62 mappings."""

    @staticmethod
    def extract_key_paths(data: Any, prefix: str = "") -> list[str]:
        """
        Extract all unique leaf key paths from a JSON-like structure in depth-first order.

        Args:
            data: A dict/list/primitive Python value (parsed JSON).
            prefix: Dot-notation prefix for nested keys (used during recursion).

        Returns:
            Ordered list of unique dot-notation key paths.
        """
        paths: list[str] = []
        seen: set[str] = set()
        KeyCompactor._collect_paths(data, prefix, paths, seen)
        return paths

    @staticmethod
    def _collect_paths(
        data: Any,
        prefix: str,
        paths: list[str],
        seen: set[str],
    ) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                full_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    KeyCompactor._collect_paths(value, full_path, paths, seen)
                elif isinstance(value, list):
                    # Always include the array path itself so it gets an index
                    if full_path not in seen:
                        seen.add(full_path)
                        paths.append(full_path)
                        
                    # For arrays, scan the first dict element to discover keys
                    first_obj = next((item for item in value if isinstance(item, dict)), None)
                    if first_obj is not None:
                        KeyCompactor._collect_paths(first_obj, full_path, paths, seen)
                else:
                    if full_path not in seen:
                        seen.add(full_path)
                        paths.append(full_path)
        elif isinstance(data, list):
            first_obj = next((item for item in data if isinstance(item, dict)), None)
            if first_obj is not None:
                KeyCompactor._collect_paths(first_obj, prefix, paths, seen)
        else:
            if prefix and prefix not in seen:
                seen.add(prefix)
                paths.append(prefix)

    @staticmethod
    def build_mapping(key_paths: list[str]) -> dict[str, str]:
        """
        Build a dictionary mapping integer string indices to original key paths.

        Args:
            key_paths: Ordered list of unique key paths.

        Returns:
            Dictionary mapping index (as string) -> original path.
        """
        mapping: dict[str, str] = {}
        for index, path in enumerate(key_paths):
            mapping[str(index)] = path
        return mapping


class JsonTransformer:
    """Bidirectional JSON tree transformer for SQUASH compact/expand operations."""

    @staticmethod
    def compact(original: Any, reverse_mapping: dict[str, str]) -> Any:
        """
        Compact a JSON structure into a flat dict with integer string keys.

        Args:
            original: The original JSON-like Python value.
            reverse_mapping: Original key path → Base62 short key.

        Returns:
            Compacted flat dict.
        """
        if isinstance(original, dict):
            flat: list[Any] = []
            JsonTransformer._flatten_and_compact(original, "", reverse_mapping, flat)
            
            # Trim trailing None values (null padding)
            while flat and flat[-1] is None:
                flat.pop()
                
            return flat
        elif isinstance(original, list):
            return JsonTransformer._compact_array(original, reverse_mapping)
        return original

    @staticmethod
    def _set_in_array(arr: list[Any], index: int, value: Any) -> None:
        if index >= len(arr):
            arr.extend([None] * (index - len(arr) + 1))
        arr[index] = value

    @staticmethod
    def _flatten_and_compact(
        data: Any,
        prefix: str,
        reverse_mapping: dict[str, str],
        result: list[Any],
    ) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                full_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    JsonTransformer._flatten_and_compact(value, full_path, reverse_mapping, result)
                elif isinstance(value, list):
                    short_key = reverse_mapping.get(full_path)
                    if short_key is not None:
                        # Array of primitives
                        JsonTransformer._set_in_array(result, int(short_key), value)
                    else:
                        # Array of objects — compact each element
                        compacted = JsonTransformer._compact_array(
                            value, reverse_mapping, full_path
                        )
                        array_short_key = reverse_mapping.get(full_path, full_path)
                        JsonTransformer._set_in_array(result, int(array_short_key), compacted)
                else:
                    short_key = reverse_mapping.get(full_path)
                    if short_key is not None:
                        JsonTransformer._set_in_array(result, int(short_key), value)
        else:
            short_key = reverse_mapping.get(prefix)
            if short_key is not None:
                JsonTransformer._set_in_array(result, int(short_key), data)

    @staticmethod
    def _compact_array(
        array: list[Any],
        reverse_mapping: dict[str, str],
        parent_path: str = "",
    ) -> list[Any]:
        result = []
        for item in array:
            if isinstance(item, dict):
                flat: list[Any] = []
                JsonTransformer._flatten_and_compact(item, parent_path, reverse_mapping, flat)
                
                # Trim trailing None values
                while flat and flat[-1] is None:
                    flat.pop()
                    
                result.append(flat)
            else:
                result.append(item)
        return result

    @staticmethod
    def expand(compacted: Any, mapping: dict[str, str]) -> Any:
        """
        Expand a compacted JSON structure back to its original nested form.
        """
        if isinstance(compacted, list):
            # New Positional Array format
            return JsonTransformer._expand_positional_array(compacted, "", mapping)
        elif isinstance(compacted, dict):
            # Legacy Object format (backwards compatibility)
            return JsonTransformer._expand_object(compacted, mapping)
        return compacted

    @staticmethod
    def _is_object_path(path: str, mapping: dict[str, str]) -> bool:
        """Check if a path has children in the mapping, meaning it's an object."""
        prefix = f"{path}." if path else ""
        return any(v.startswith(prefix) for v in mapping.values())
        
    @staticmethod
    def _is_array_of_objects(path: str, mapping: dict[str, str]) -> bool:
        """Check if a path is an array of objects by seeing if it has children."""
        return JsonTransformer._is_object_path(path, mapping)

    @staticmethod
    def _expand_positional_array(arr: list[Any], current_path: str, mapping: dict[str, str]) -> dict[str, Any]:
        nested: dict[str, Any] = {}
        
        for index, value in enumerate(arr):
            if value is None:
                continue
                
            # Find the original path for this index
            original_path = mapping.get(str(index))
            if not original_path:
                continue
                
            # If we are parsing a nested object, only process keys that belong to it
            if current_path and not original_path.startswith(f"{current_path}."):
                continue
                
            # If value is a list, it could be an array of primitives, array of objects, or a nested object
            if isinstance(value, list):
                if JsonTransformer._is_array_of_objects(original_path, mapping):
                    # Array of objects: iterate and parse each as a positional array
                    value = [JsonTransformer._expand_positional_array(item, original_path, mapping) for item in value]
                elif JsonTransformer._is_object_path(original_path, mapping):
                    # Nested object: parse as positional array
                    value = JsonTransformer._expand_positional_array(value, original_path, mapping)
                # Else it's an array of primitives (keep as is)

            JsonTransformer._unflatten(nested, original_path, value)

        # If current_path is set, we need to extract only the subtree
        if current_path:
            parts = current_path.split(".")
            curr = nested
            for p in parts:
                curr = curr.get(p, {})
            return curr
            
        return nested

    @staticmethod
    def _expand_object(obj: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
        nested: dict[str, Any] = {}
        for short_key, value in obj.items():
            original_path = mapping.get(short_key, short_key)
            parts = original_path.split(".")

            # Expand array values recursively
            if isinstance(value, list):
                value = [JsonTransformer.expand(item, mapping) for item in value]

            # Set value at the nested path
            current = nested
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value

        return nested
