from __future__ import annotations

import json

import httpx

from .conftest import build_app, client_for, conversation_files, streaming_response


def _usage_handler(prompt: int, completion: int):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "id": "x",
            "object": "chat.completion",
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
        return streaming_response(200, json.dumps(body).encode())

    return handler


async def test_top_block_shows_latest_turn_context(config):
    config.smart_zone_tokens = 100000
    app = build_app(config, _usage_handler(74000, 15000))
    request = {"model": "deepseek-flash", "messages": [{"role": "user", "content": "Hi"}]}
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request)

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    top = text.split("## Turn 1", 1)[0]
    assert "**Prompt token:  74,000 prompt (74% of 100k)**" in top
    assert "Total token: 89,000" in top
    assert "最新一轮上下文已用 74% 的 smart zone。" in top


async def test_top_block_uses_latest_turn_only(config):
    config.smart_zone_tokens = 100000
    app = build_app(config, _usage_handler(1000, 1000))
    messages = [{"role": "user", "content": "Hi"}]
    request1 = {"model": "deepseek-flash", "messages": messages}
    request2 = {
        "model": "deepseek-flash",
        "messages": messages + [{"role": "assistant", "content": "4"}, {"role": "user", "content": "More"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request1)
        await client.post("/chat/completions", json=request2)

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    top = text.split("## Turn 1", 1)[0]
    assert "2,000" in top


async def test_warning_appears_over_threshold(config):
    config.smart_zone_tokens = 100000
    app = build_app(config, _usage_handler(90000, 5000))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions", json={"messages": [{"role": "user", "content": "Hi"}]}
        )

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    top = text.split("## Turn 1", 1)[0]
    assert "\u26a0" in top


async def test_no_warning_below_threshold(config):
    config.smart_zone_tokens = 100000
    app = build_app(config, _usage_handler(50000, 5000))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions", json={"messages": [{"role": "user", "content": "Hi"}]}
        )

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    top = text.split("## Turn 1", 1)[0]
    assert "\u26a0" not in top


async def test_top_block_omitted_without_usage(config):
    app = build_app(
        config,
        lambda request: streaming_response(200, b'{"choices":[{"message":{"role":"assistant","content":"4"},"finish_reason":"stop"}]}'),
    )
    async with client_for(app) as client:
        await client.post(
            "/chat/completions", json={"messages": [{"role": "user", "content": "Hi"}]}
        )

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    assert "Prompt token:" not in text
    assert "Total token:" not in text
