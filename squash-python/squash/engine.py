"""
SQUASH Engine — main entry point for encoding and decoding JSON payloads.

This is the Python equivalent of the Kotlin SquashEngine, providing the
same encode/decode/dict-sync interface.
"""

from __future__ import annotations

from typing import Any

from squash.compactor import JsonTransformer
from squash.dictionary import DictionaryBuilder, DictionaryStore, SquashDictionary


class SquashEngine:
    """
    Main SQUASH protocol engine.

    Manages dictionary caching and provides methods for encoding JSON payloads
    into compact SQUASH envelopes, and decoding them back.
    """

    def __init__(self, dict_store: DictionaryStore | None = None) -> None:
        self.dict_store = dict_store or DictionaryStore()

    def encode(
        self,
        original: Any,
        schema_name: str,
        client_dict_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Encode a JSON-like Python value into an SQUASH envelope dict.

        Args:
            original: The original JSON data (dict/list/primitive).
            schema_name: Logical schema name (e.g., "user").
            client_dict_id: The client's cached dictId, if any.

        Returns:
            SQUASH envelope as a dict ready for JSON serialization.
        """
        # Get or build dictionary
        dictionary = self.dict_store.get(schema_name)
        if dictionary is None:
            dictionary = DictionaryBuilder.build(schema_name, 1, original)
            self.dict_store.put(dictionary)

        # Compact the payload
        compacted = JsonTransformer.compact(original, dictionary.reverse_mapping)

        # Determine whether to include the dictionary
        include_dict = self.should_include_dict(dictionary.dict_id, client_dict_id)

        envelope: dict[str, Any] = {
            "__meta": {
                "v": 1,
                "dictId": dictionary.dict_id,
                "encoding": "array",
            },
            "d": compacted,
        }

        if include_dict:
            envelope["__dict"] = dictionary.mapping

        return envelope

    def encode_with_dict(
        self,
        original: Any,
        dictionary: SquashDictionary,
        client_dict_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Encode using a pre-existing dictionary.

        Args:
            original: The original JSON data.
            dictionary: The dictionary to use.
            client_dict_id: The client's cached dictId, if any.

        Returns:
            SQUASH envelope dict.
        """
        self.dict_store.put(dictionary)
        compacted = JsonTransformer.compact(original, dictionary.reverse_mapping)
        include_dict = self.should_include_dict(dictionary.dict_id, client_dict_id)

        envelope: dict[str, Any] = {
            "__meta": {
                "v": 1,
                "dictId": dictionary.dict_id,
                "encoding": "array",
            },
            "d": compacted,
        }
        if include_dict:
            envelope["__dict"] = dictionary.mapping

        return envelope

    def decode(self, envelope: dict[str, Any]) -> Any:
        """
        Decode an SQUASH envelope back into the original JSON structure.

        If the envelope contains ``__dict``, it is cached for future use.

        Args:
            envelope: The SQUASH envelope dict.

        Returns:
            The expanded original JSON data.

        Raises:
            ValueError: If no dictionary is available for the envelope's dictId.
        """
        meta = envelope["__meta"]
        dict_id = meta["dictId"]
        dict_mapping = envelope.get("__dict")

        if dict_mapping is not None:
            version = self._extract_version(dict_id)
            dictionary = SquashDictionary(
                dict_id=dict_id,
                version=version,
                mapping=dict_mapping,
            )
            self.dict_store.put(dictionary)
            mapping = dict_mapping
        else:
            cached = self.dict_store.get_by_dict_id(dict_id)
            if cached is None:
                raise ValueError(
                    f"No dictionary found for dictId '{dict_id}'. "
                    "The server should have included __dict in the response."
                )
            mapping = cached.mapping

        return JsonTransformer.expand(envelope["d"], mapping)

    def should_include_dict(
        self, server_dict_id: str, client_dict_id: str | None
    ) -> bool:
        """
        Determine whether __dict should be included in the response envelope.

        Returns True when:
        - Client has no cached dict (client_dict_id is None)
        - Client's cached dict doesn't match server's current version
        """
        if client_dict_id is None:
            return True
        return client_dict_id != server_dict_id

    def register_dictionary(self, dictionary: SquashDictionary) -> None:
        """Register a pre-built dictionary in the store."""
        self.dict_store.put(dictionary)

    @staticmethod
    def _extract_version(dict_id: str) -> int:
        """Extract version number from a dictId string."""
        try:
            return int(dict_id.rsplit("_v", 1)[1])
        except (IndexError, ValueError):
            return 1
