"""
Utility functions for SQUASH.

Provides helpers for JSON serialization (orjson when available, stdlib json fallback),
and dict flatten/unflatten.
"""

from __future__ import annotations

import json as _json
from typing import Any

# orjson is optional — use stdlib json as fallback
try:
    import orjson

    def json_dumps(data: Any) -> bytes:
        """Serialize to JSON bytes using orjson for maximum performance."""
        return orjson.dumps(data)

    def json_loads(data: bytes | str) -> Any:
        """Deserialize JSON bytes or string using orjson."""
        return orjson.loads(data)

except ImportError:

    def json_dumps(data: Any) -> bytes:
        """Serialize to JSON bytes using stdlib json."""
        return _json.dumps(data, separators=(",", ":")).encode("utf-8")

    def json_loads(data: bytes | str) -> Any:
        """Deserialize JSON bytes or string using stdlib json."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return _json.loads(data)


def flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Flatten a nested dict into dot-notation keys.

    Example::

        >>> flatten_dict({"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}})
        {"user.name": "Ashwin", "user.address.city": "Mumbai"}
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, full_key))
        else:
            result[full_key] = value
    return result


def unflatten_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Unflatten a dot-notation dict back to a nested structure.

    Example::

        >>> unflatten_dict({"user.name": "Ashwin", "user.address.city": "Mumbai"})
        {"user": {"name": "Ashwin", "address": {"city": "Mumbai"}}}
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def calculate_compression_ratio(original: Any, compacted: Any) -> float:
    """
    Calculate the compression ratio between original and compacted JSON.

    Returns a value between 0 and 1 where lower is better compression.
    """
    original_size = len(json_dumps(original))
    compacted_size = len(json_dumps(compacted))
    if original_size == 0:
        return 1.0
    return compacted_size / original_size
