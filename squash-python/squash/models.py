"""
Pydantic models for SQUASH protocol structures.

These models provide validation and serialization for the SQUASH envelope format.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SquashMeta(BaseModel):
    """Protocol metadata block carried inside every SQUASH envelope."""

    v: int = Field(default=1, description="Protocol version")
    dictId: str = Field(description="Dictionary identifier in {schema}_v{version} format")  # noqa: N815
    encoding: str = Field(default="map", description="Encoding mode")


class SquashEnvelope(BaseModel):
    """
    SQUASH protocol envelope — the top-level wire format.

    We use ``model_config`` with ``populate_by_name=True`` so that
    the model can be populated using both alias and field name.

    Example wire format:
        {
            "__meta": {"v": 1, "dictId": "user_v1", "encoding": "map"},
            "__dict": {"a": "user.name", "b": "user.email"},
            "d": {"a": "Ashwin", "b": "ashwin@email.com"}
        }
    """

    meta: SquashMeta = Field(alias="__meta")
    dict_mapping: dict[str, str] | None = Field(default=None, alias="__dict")
    d: Any = Field(description="Compacted payload")

    model_config = {"populate_by_name": True}

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the SQUASH wire format dict."""
        result: dict[str, Any] = {
            "__meta": {
                "v": self.meta.v,
                "dictId": self.meta.dictId,
                "encoding": self.meta.encoding,
            },
            "d": self.d,
        }
        if self.dict_mapping is not None:
            result["__dict"] = self.dict_mapping
        return result

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> SquashEnvelope:
        """Deserialize from an SQUASH wire format dict."""
        return cls(
            meta=SquashMeta(**data["__meta"]),
            dict_mapping=data.get("__dict"),
            d=data["d"],
        )
