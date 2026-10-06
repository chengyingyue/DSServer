from __future__ import annotations

import httpx

from .conftest import build_app, client_for, streaming_response


async def test_get_is_forwarded_and_body_returned_unchanged(config):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://upstream.test/models"
        return streaming_response(200, b'{"data": []}', {"x-upstream": "yes"})

    app = build_app(config, handler)
    async with client_for(app) as client:
        response = await client.get("/models")

    assert response.status_code == 200
    assert response.content == b'{"data": []}'
    assert response.headers["x-upstream"] == "yes"


async def test_post_body_is_forwarded_unchanged(config):
    seen: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return streaming_response(200, b'{"ok": true}')

    app = build_app(config, handler)
    async with client_for(app) as client:
        response = await client.post("/chat/completions", content=b'{"model": "x"}')

    assert seen["body"] == b'{"model": "x"}'
    assert response.content == b'{"ok": true}'


async def test_error_response_is_passed_through_unchanged(config):
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(429, b'{"error": "rate limited"}')

    app = build_app(config, handler)
    async with client_for(app) as client:
        response = await client.post("/chat/completions", content=b"{}")

    assert response.status_code == 429
    assert response.content == b'{"error": "rate limited"}'


async def test_query_string_is_preserved(config):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://upstream.test/models?limit=5"
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.get("/models?limit=5")


async def test_upstream_is_asked_for_identity_encoding(config):
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["accept-encoding"] = request.headers.get("accept-encoding")
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.get("/models")

    assert seen["accept-encoding"] == "identity"


async def test_authorization_header_is_forwarded_upstream(config):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            content=b"{}",
            headers={"Authorization": "Bearer secret"},
        )

    assert seen["auth"] == "Bearer secret"
