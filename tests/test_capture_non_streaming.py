from __future__ import annotations

import asyncio
import json

import httpx

from .conftest import Handler, build_app, client_for, read_records, streaming_response

CHAT_REQUEST = {
    "model": "deepseek-flash",
    "messages": [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ],
    "temperature": 0.7,
}

CHAT_RESPONSE = {
    "id": "abc",
    "object": "chat.completion",
    "model": "deepseek-flash",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hi there"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
}


def chat_handler(response: dict) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(200, json.dumps(response).encode())

    return handler


async def test_successful_chat_is_recorded_with_full_exchange(config):
    app = build_app(config, chat_handler(CHAT_RESPONSE))
    async with client_for(app) as client:
        response = await client.post(
            "/chat/completions",
            json=CHAT_REQUEST,
            headers={"Authorization": "Bearer sk-secret", "User-Agent": "TestApp/1.0", "X-Custom": "nope"},
        )

    assert response.status_code == 200
    assert response.json() == CHAT_RESPONSE

    records = read_records(config)
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "chat"
    assert record["owner"] == "local"
    assert record["request"]["messages"] == CHAT_REQUEST["messages"]
    assert record["request"]["model"] == "deepseek-flash"
    assert record["request"]["stream"] is False
    assert record["request"]["params"] == {"temperature": 0.7}
    assert record["response"]["message"]["content"] == "Hi there"
    assert record["response"]["finish_reason"] == "stop"
    assert record["response"]["usage"]["total_tokens"] == 8
    assert record["meta"]["latency_ms"] >= 0


async def test_authorization_header_is_never_stored(config):
    app = build_app(config, chat_handler(CHAT_RESPONSE))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            json=CHAT_REQUEST,
            headers={"Authorization": "Bearer sk-secret"},
        )

    record = read_records(config)[0]
    assert "authorization" not in record["client"]["headers"]
    assert "sk-secret" not in json.dumps(record)


async def test_only_whitelisted_headers_are_stored(config):
    app = build_app(config, chat_handler(CHAT_RESPONSE))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            json=CHAT_REQUEST,
            headers={"User-Agent": "TestApp/1.0", "X-Custom": "nope"},
        )

    client_info = read_records(config)[0]["client"]
    assert client_info["user_agent"] == "TestApp/1.0"
    assert client_info["headers"]["user-agent"] == "TestApp/1.0"
    assert "x-custom" not in client_info["headers"]


async def test_authorization_is_never_stored_even_if_whitelisted(config):
    config.header_whitelist = [*config.header_whitelist, "authorization"]
    app = build_app(config, chat_handler(CHAT_RESPONSE))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            json=CHAT_REQUEST,
            headers={"Authorization": "Bearer sk-secret"},
        )

    record = read_records(config)[0]
    assert "authorization" not in record["client"]["headers"]
    assert "sk-secret" not in json.dumps(record)


async def test_non_chat_request_is_recorded_as_metadata_only(config):
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(200, b'{"data": []}')

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.get("/models")

    record = read_records(config)[0]
    assert record["kind"] == "other"
    assert record["request"] == {"method": "GET", "path": "/models"}
    assert record["response"] == {"status": 200}
    assert record["meta"]["latency_ms"] >= 0


async def test_failed_chat_is_recorded_as_metadata_only(config):
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(429, b'{"error": "rate limited"}')

    app = build_app(config, handler)
    async with client_for(app) as client:
        response = await client.post("/chat/completions", json=CHAT_REQUEST)

    assert response.status_code == 429
    record = read_records(config)[0]
    assert record["kind"] == "other"
    assert record["response"] == {"status": 429}


async def test_concurrent_writes_do_not_corrupt_the_log(config):
    app = build_app(config, chat_handler(CHAT_RESPONSE))
    async with client_for(app) as client:
        await asyncio.gather(
            *[client.post("/chat/completions", json=CHAT_REQUEST) for _ in range(20)]
        )

    raw_lines = config.log_path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 20
    for line in raw_lines:
        json.loads(line)
