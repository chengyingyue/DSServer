from __future__ import annotations

import httpx

from .conftest import Handler, build_app, client_for, read_records, streaming_response

STREAM_REQUEST = {
    "model": "deepseek-flash",
    "stream": True,
    "messages": [{"role": "user", "content": "Hello"}],
}

SSE = (
    b'data: {"id":"1","choices":[{"index":0,"delta":{"role":"assistant","content":"","reasoning_content":"Think"}}]}\n\n'
    b'data: {"id":"1","choices":[{"index":0,"delta":{"content":"Hello"}}]}\n\n'
    b'data: {"id":"1","choices":[{"index":0,"delta":{"content":" world"}}]}\n\n'
    b'data: {"id":"1","choices":[{"index":0,"delta":{"content":""},"finish_reason":"stop"}],'
    b'"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}\n\n'
    b'data: [DONE]\n\n'
)

TOOL_SSE = (
    b'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_1",'
    b'"type":"function","function":{"name":"get_weather","arguments":"{\\"ci"}}]}}]}\n\n'
    b'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
    b'"function":{"arguments":"ty\\":\\"Paris\\"}"}}]}}]}\n\n'
    b"data: [DONE]\n\n"
)


def sse_handler(payload: bytes) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(200, payload, {"content-type": "text/event-stream"})

    return handler


async def test_streaming_response_is_relayed_byte_faithfully(config):
    app = build_app(config, sse_handler(SSE))
    async with client_for(app) as client:
        response = await client.post("/chat/completions", json=STREAM_REQUEST)

    assert response.status_code == 200
    assert response.content == SSE


async def test_streaming_exchange_is_recorded(config):
    app = build_app(config, sse_handler(SSE))
    async with client_for(app) as client:
        await client.post("/chat/completions", json=STREAM_REQUEST)

    record = read_records(config)[0]
    assert record["kind"] == "chat"
    assert record["request"]["stream"] is True
    message = record["response"]["message"]
    assert message["content"] == "Hello world"
    assert message["reasoning_content"] == "Think"
    assert record["response"]["finish_reason"] == "stop"
    assert record["response"]["usage"]["total_tokens"] == 7


async def test_raw_sse_is_stored_when_configured(config):
    assert config.keep_raw_sse is True
    app = build_app(config, sse_handler(SSE))
    async with client_for(app) as client:
        await client.post("/chat/completions", json=STREAM_REQUEST)

    record = read_records(config)[0]
    assert record["raw_sse"] == SSE.decode()


async def test_raw_sse_is_omitted_when_disabled(config):
    config.keep_raw_sse = False
    app = build_app(config, sse_handler(SSE))
    async with client_for(app) as client:
        await client.post("/chat/completions", json=STREAM_REQUEST)

    record = read_records(config)[0]
    assert "raw_sse" not in record


async def test_tool_call_deltas_are_merged(config):
    app = build_app(config, sse_handler(TOOL_SSE))
    async with client_for(app) as client:
        await client.post("/chat/completions", json=STREAM_REQUEST)

    message = read_records(config)[0]["response"]["message"]
    assert message["tool_calls"][0]["id"] == "call_1"
    assert message["tool_calls"][0]["function"]["name"] == "get_weather"
    assert message["tool_calls"][0]["function"]["arguments"] == '{"city":"Paris"}'
