from __future__ import annotations

import httpx

from .conftest import build_app, client_for


def _usage_handler(prompt: int, completion: int):
    import json

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "model": "deepseek-flash",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": "4"}, "finish_reason": "stop"}
            ],
            "usage": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": prompt + completion,
            },
        }
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(body).encode()))

    return handler


async def test_console_prints_token_summary(config, capsys):
    config.smart_zone_tokens = 100000
    app = build_app(config, _usage_handler(74000, 15000))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions", json={"messages": [{"role": "user", "content": "Hi"}]}
        )

    out = capsys.readouterr().out
    assert "prompt=74,000" in out
    assert "completion=15,000" in out
    assert "total=89,000" in out
    assert "ctx=74,000/100k (74%)" in out


async def test_console_prints_for_streaming(config, capsys):
    from .test_capture_streaming import SSE, STREAM_REQUEST, sse_handler

    app = build_app(config, sse_handler(SSE))
    async with client_for(app) as client:
        await client.post("/chat/completions", json=STREAM_REQUEST)

    out = capsys.readouterr().out
    assert "prompt=5" in out
    assert "total=7" in out
