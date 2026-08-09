"""
SQUASH Dictionary management — store and builder.

DictionaryStore: Thread-safe in-memory cache for versioned dictionaries.
DictionaryBuilder: Builds dictionaries from sample JSON data.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import threading
from typing import Any

from squash.compactor import KeyCompactor


@dataclass
class SquashDictionary:
    """
    Represents a versioned SQUASH dictionary mapping Base62 short keys
    to original fully-qualified JSON key paths.

    Attributes:
        dict_id: Unique identifier in ``{schema}_v{version}`` format.
        version: Monotonically increasing version number.
        mapping: Short-key → original-key-path mapping.
    """

    dict_id: str
    version: int
    mapping: dict[str, str]

    @cached_property
    def reverse_mapping(self) -> dict[str, str]:
        """Original key path → short key. Used during compaction."""
        return {v: k for k, v in self.mapping.items()}

    @property
    def schema_name(self) -> str:
        """Schema name portion of the dict_id (e.g., 'user' from 'user_v1')."""
        return self.dict_id.rsplit("_v", 1)[0]


class DictionaryStore:
    """
    Thread-safe in-memory store for SQUASH dictionaries.

    Dictionaries are keyed by schema name and only the latest version is kept.
    """

    def __init__(self) -> None:
        self._store: dict[str, SquashDictionary] = {}
        self._lock = threading.Lock()

    def put(self, dictionary: SquashDictionary) -> bool:
        """
        Store or update a dictionary. Only replaces if the new version is higher.

        Returns:
            True if stored (new or higher version), False if skipped.
        """
        with self._lock:
            existing = self._store.get(dictionary.schema_name)
            if existing is not None and existing.version >= dictionary.version:
                return False
            self._store[dictionary.schema_name] = dictionary
            return True

    def get(self, schema_name: str) -> SquashDictionary | None:
        """Retrieve the cached dictionary for a schema name."""
        with self._lock:
            return self._store.get(schema_name)

    def get_by_dict_id(self, dict_id: str) -> SquashDictionary | None:
        """Retrieve a dictionary by its full dictId."""
        schema_name = dict_id.rsplit("_v", 1)[0]
        with self._lock:
            d = self._store.get(schema_name)
            return d if d and d.dict_id == dict_id else None

    def is_current(self, server_dict_id: str) -> bool:
        """Check if the client's dict matches the server's dictId."""
        return self.get_by_dict_id(server_dict_id) is not None

    def get_dict_id(self, schema_name: str) -> str | None:
        """Returns the dictId for a schema, or None."""
        with self._lock:
            d = self._store.get(schema_name)
            return d.dict_id if d else None

    def remove(self, schema_name: str) -> None:
        """Remove the dictionary for a schema."""
        with self._lock:
            self._store.pop(schema_name, None)

    def clear(self) -> None:
        """Clear all cached dictionaries."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Number of cached dictionaries."""
        with self._lock:
            return len(self._store)


class DictionaryBuilder:
    """Builds SQUASH dictionaries from sample JSON data."""

    @staticmethod
    def build(schema_name: str, version: int, sample_data: Any) -> SquashDictionary:
        """
        Build a dictionary from a sample JSON-like Python value.

        Args:
            schema_name: Logical schema name (e.g., "user").
            version: Dictionary version number.
            sample_data: Representative JSON data whose structure defines the schema.

        Returns:
            A new SquashDictionary with Base62-encoded key mappings.
        """
        key_paths = KeyCompactor.extract_key_paths(sample_data)
        mapping = KeyCompactor.build_mapping(key_paths)
        return SquashDictionary(
            dict_id=f"{schema_name}_v{version}",
            version=version,
            mapping=mapping,
        )

    @staticmethod
    def build_from_paths(
        schema_name: str, version: int, key_paths: list[str]
    ) -> SquashDictionary:
        """
        Build a dictionary from an explicit list of key paths.

        Args:
            schema_name: Logical schema name.
            version: Dictionary version number.
            key_paths: Ordered list of dot-notation key paths.

        Returns:
            A new SquashDictionary.
        """
        mapping = KeyCompactor.build_mapping(key_paths)
        return SquashDictionary(
            dict_id=f"{schema_name}_v{version}",
            version=version,
            mapping=mapping,
        )
