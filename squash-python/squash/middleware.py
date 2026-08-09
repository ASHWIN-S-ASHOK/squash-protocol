"""
FastAPI / ASGI middleware for transparent SQUASH protocol negotiation.

Inspects incoming request headers for SQUASH support and automatically
encodes response payloads when the client declares compatibility.
"""

from __future__ import annotations

from squash.utils import json_dumps, json_loads

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from squash.engine import SquashEngine
from squash.v2 import BinarySquashEngine

# Header constants
MIME_SQUASH_PROTO = "application/squash+proto"
HEADER_ACCEPT_ENCODING = "accept-encoding"
HEADER_CONTENT_ENCODING = "content-encoding"
HEADER_SQUASH_DICT_ID = "x-squash-dictid"
ENCODING_SQUASH = "squash"


class SquashMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that transparently handles SQUASH protocol negotiation.

    When a client sends ``Accept-Encoding: squash``, this middleware:
    1. Reads the response JSON body
    2. Encodes it as an SQUASH envelope using the configured schema
    3. Sets ``Content-Encoding: squash`` and ``X-SQUASH-DictId`` response headers
    4. Conditionally includes ``__dict`` based on client's cached dict version

    Usage::

        from fastapi import FastAPI
        from squash.middleware import SquashMiddleware

        app = FastAPI()
        app.add_middleware(SquashMiddleware, schema_name="api")
    """

    def __init__(
        self,
        app,
        schema_name: str = "default",
        engine: SquashEngine | None = None,
    ) -> None:
        """
        Args:
            app: The ASGI application.
            schema_name: Default schema name for dictionary management.
            engine: Optional shared SquashEngine instance.
        """
        super().__init__(app)
        self.schema_name = schema_name
        self.engine = engine or SquashEngine()
        self.binary_engine = BinarySquashEngine()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Check if client supports SQUASH v2 Binary
        accept_header = request.headers.get("accept", "")
        supports_v2 = MIME_SQUASH_PROTO in accept_header

        # Check if client supports SQUASH v1 JSON
        accept_encoding = request.headers.get(HEADER_ACCEPT_ENCODING, "")
        supports_v1 = ENCODING_SQUASH in accept_encoding

        if not supports_v1 and not supports_v2:
            # Client doesn't support SQUASH — pass through
            return await call_next(request)

        # Get client's cached dict ID
        client_dict_id = request.headers.get(HEADER_SQUASH_DICT_ID)

        # Get the response from the actual endpoint
        response = await call_next(request)

        # Only process JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read the response body
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(chunk)
        body = b"".join(body_chunks)

        try:
            # Parse the original JSON response
            original_data = json_loads(body)

            # Determine schema name from endpoint or use default
            schema = self._resolve_schema(request)

            if supports_v2:
                # SQUASH v2 Binary path
                binary_frame = self.binary_engine.to_binary_frame(
                    data=original_data,
                    schema_name=schema,
                    client_dict_id=client_dict_id,
                )
                headers = dict(response.headers)
                headers["content-type"] = MIME_SQUASH_PROTO
                # Note: v2 dictionary ID is inside the frame itself, but we can set header too if desired
                headers["content-length"] = str(len(binary_frame))

                return Response(
                    content=binary_frame,
                    status_code=response.status_code,
                    headers=headers,
                )
            else:
                # SQUASH v1 JSON path
                envelope = self.engine.encode(
                    original=original_data,
                    schema_name=schema,
                    client_dict_id=client_dict_id,
                )
                encoded_body = json_dumps(envelope)

                headers = dict(response.headers)
                headers[HEADER_CONTENT_ENCODING] = ENCODING_SQUASH
                headers[HEADER_SQUASH_DICT_ID] = envelope["__meta"]["dictId"]
                headers["content-type"] = "application/json"
                headers["content-length"] = str(len(encoded_body))

                return Response(
                    content=encoded_body,
                    status_code=response.status_code,
                    headers=headers,
                )

        except Exception:
            # If encoding fails, return original response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    def _resolve_schema(self, request: Request) -> str:
        """
        Resolve the schema name for a request.

        Uses ``X-SQUASH-Schema`` header if present, falls back to the
        configured default schema name.
        """
        return request.headers.get("x-squash-schema", self.schema_name)
