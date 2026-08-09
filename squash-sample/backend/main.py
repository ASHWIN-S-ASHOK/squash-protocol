"""
SQUASH Sample Backend — FastAPI application demonstrating SQUASH middleware.

This server provides sample API endpoints that automatically serve
SQUASH-encoded responses when clients declare support via headers.

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import sys
import os

# Add squash-python to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "squash-python"))

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from squash.engine import SquashEngine
from squash.middleware import SquashMiddleware

from schemas import SAMPLE_PRODUCTS, SAMPLE_USERS, SAMPLE_COMPLEX

# ─── App Setup ────────────────────────────────────────────────

app = FastAPI(
    title="SQUASH Sample Backend",
    description="Demonstrates the Hybrid JSON Compact Protocol with FastAPI",
    version="0.1.0",
)

# Shared engine instance so all endpoints share dictionary cache
engine = SquashEngine()

# Add SQUASH middleware — automatically handles header negotiation
app.add_middleware(SquashMiddleware, schema_name="api", engine=engine)


# ─── Endpoints ────────────────────────────────────────────────


@app.get("/")
async def root():
    """Health check / info endpoint."""
    return {
        "service": "squash-sample-backend",
        "version": "0.1.0",
        "protocol": "SQUASH v1",
        "endpoints": ["/users", "/users/{id}", "/products", "/products/{id}"],
    }


@app.get("/users")
async def list_users():
    """List all users — demonstrates list-of-objects compaction."""
    return [user.model_dump() for user in SAMPLE_USERS]


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get a single user — demonstrates nested object compaction."""
    user = next((u for u in SAMPLE_USERS if u.id == user_id), None)
    if user is None:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return user.model_dump()


@app.get("/products")
async def list_products():
    """List all products — demonstrates wide-schema compaction."""
    return [product.model_dump() for product in SAMPLE_PRODUCTS]


@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get a single product."""
    product = next((p for p in SAMPLE_PRODUCTS if p.id == product_id), None)
    if product is None:
        return JSONResponse(status_code=404, content={"error": "Product not found"})
    return product.model_dump()


@app.get("/complex")
async def get_complex():
    """Get a deeply nested object with diverse data types."""
    return SAMPLE_COMPLEX.model_dump()


@app.get("/debug/dict-store")
async def debug_dict_store():
    """Debug endpoint — shows the current state of the dictionary store."""
    store = engine.dict_store
    schemas = {}
    # Inspect internal store
    for schema_name, dictionary in store._store.items():
        schemas[schema_name] = {
            "dictId": dictionary.dict_id,
            "version": dictionary.version,
            "keyCount": len(dictionary.mapping),
            "mapping": dictionary.mapping,
        }
    return {"dictionaries": schemas, "count": store.size}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
