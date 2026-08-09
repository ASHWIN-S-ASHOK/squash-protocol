"""Tests for the SQUASH FastAPI middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from squash.middleware import SquashMiddleware


def _create_app() -> FastAPI:
    """Create a minimal FastAPI app with SQUASH middleware for testing."""
    app = FastAPI()
    app.add_middleware(SquashMiddleware, schema_name="test")

    @app.get("/user")
    async def get_user():
        return {"name": "Ashwin", "email": "ashwin@email.com", "age": 28}

    @app.get("/nested")
    async def get_nested():
        return {
            "user": {
                "name": "Ashwin",
                "address": {"city": "Mumbai", "zip": "400001"},
            }
        }

    @app.get("/text")
    async def get_text():
        from starlette.responses import PlainTextResponse
        return PlainTextResponse("hello")

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_create_app())


class TestSquashMiddleware:
    """Test the SQUASH middleware integration."""

    def test_non_squash_client_gets_plain_json(self, client: TestClient):
        """Client without Accept-Encoding: squash gets standard JSON."""
        response = client.get("/user")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ashwin"
        assert "__meta" not in data  # No SQUASH envelope

    def test_squash_client_gets_envelope(self, client: TestClient):
        """Client with Accept-Encoding: squash gets SQUASH envelope."""
        response = client.get("/user", headers={"Accept-Encoding": "squash"})
        assert response.status_code == 200

        data = response.json()
        assert "__meta" in data
        assert data["__meta"]["v"] == 1
        assert data["__meta"]["encoding"] == "map"
        assert "d" in data

    def test_first_request_includes_dict(self, client: TestClient):
        """First SQUASH request should include __dict."""
        response = client.get("/user", headers={"Accept-Encoding": "squash"})
        data = response.json()
        assert "__dict" in data
        assert isinstance(data["__dict"], dict)

    def test_response_headers(self, client: TestClient):
        """Response should include SQUASH headers."""
        response = client.get(
            "/user",
            headers={"Accept-Encoding": "squash"},
        )
        assert response.headers.get("content-encoding") == "squash"
        assert "x-squash-dictid" in response.headers

    def test_dict_omitted_when_current(self, client: TestClient):
        """When client sends current dictId, __dict should be omitted."""
        # First request to get the dict
        r1 = client.get("/user", headers={"Accept-Encoding": "squash"})
        dict_id = r1.json()["__meta"]["dictId"]

        # Second request with the dictId
        r2 = client.get(
            "/user",
            headers={
                "Accept-Encoding": "squash",
                "X-SQUASH-DictId": dict_id,
            },
        )
        data = r2.json()
        assert "__dict" not in data

    def test_nested_payload_compaction(self, client: TestClient):
        """Nested payloads should be properly compacted."""
        response = client.get("/nested", headers={"Accept-Encoding": "squash"})
        data = response.json()
        assert "__meta" in data
        assert "d" in data
        # The compacted data should have short keys
        compacted = data["d"]
        assert isinstance(compacted, dict)
        # All keys should be Base62 short codes
        for key in compacted:
            assert len(key) <= 2  # Base62 keys are short

    def test_non_json_response_passes_through(self, client: TestClient):
        """Non-JSON responses should not be touched."""
        response = client.get("/text", headers={"Accept-Encoding": "squash"})
        assert response.text == "hello"
