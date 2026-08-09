"""
SQUASH — Hybrid JSON Compact Protocol

A schema-aware transport optimization library that reduces JSON payload sizes
using dictionary encoding, key compaction, and HTTP header negotiation.
"""

from squash.engine import SquashEngine
from squash.models import SquashEnvelope, SquashMeta
from squash.dictionary import DictionaryStore, DictionaryBuilder
from squash.base62 import Base62
from squash.compactor import KeyCompactor, JsonTransformer

__version__ = "0.1.0"

__all__ = [
    "SquashEngine",
    "SquashEnvelope",
    "SquashMeta",
    "DictionaryStore",
    "DictionaryBuilder",
    "Base62",
    "KeyCompactor",
    "JsonTransformer",
    "SquashMiddleware",
    "BinarySquashEngine",
    "BinaryDictionary",
]


def __getattr__(name: str):
    """Lazy import for optional dependencies and v2."""
    if name == "SquashMiddleware":
        from squash.middleware import SquashMiddleware
        return SquashMiddleware
    if name == "BinarySquashEngine":
        from squash.v2 import BinarySquashEngine
        return BinarySquashEngine
    if name == "BinaryDictionary":
        from squash.v2 import BinaryDictionary
        return BinaryDictionary
    raise AttributeError(f"module 'squash' has no attribute {name!r}")
