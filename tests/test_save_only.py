from __future__ import annotations

import json

from .conftest import build_app, client_for, read_records


def _no_upstream(request):
    raise AssertionError("save-only request must not reach the Upstream")


async def test_save_records_without_forwarding_and_returns_marker(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-flash",
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "Remember this."},
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Remember this.\nsaved"

    records = read_records(config)
    assert len(records) == 1
    assert records[0]["kind"] == "chat"
    assert records[0]["response"]["message"]["content"] == "Remember this.\nsaved"
    assert records[0]["request"]["messages"] == request["messages"]


async def test_save_echoes_only_the_latest_user_message(config):
    app = build_app(config, _no_upstream)
    request = {
        "messages": [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "Second question\nsaved"


async def test_save_without_user_message_returns_plain_marker(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "system", "content": "Be terse."}]}
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "saved"


async def test_save_with_non_text_user_content_returns_plain_marker(config):
    app = build_app(config, _no_upstream)
    request = {
        "messages": [
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x"}}]}
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "saved"


async def test_saved_conversation_appears_in_markdown(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)

    files = sorted(config.conversations_dir.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "Remember this.\nsaved" in text
    assert "Remember this." in text


async def test_save_rejects_invalid_body(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/save", content=json.dumps({"foo": 1}))

    assert response.status_code == 400


async def test_save_streaming_returns_sse(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-chat",
        "stream": True,
        "messages": [{"role": "user", "content": "hello test"}],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert body.endswith("data: [DONE]\n\n")

    deltas = []
    finish = None
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            continue
        chunk = json.loads(payload)
        choice = chunk["choices"][0]
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
        content = choice.get("delta", {}).get("content")
        if content:
            deltas.append(content)

    assert "".join(deltas) == "hello test\nsaved"
    assert finish == "stop"


async def test_save_streaming_is_recorded_once(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-chat",
        "stream": True,
        "messages": [{"role": "user", "content": "hello test"}],
    }
    async with client_for(app) as client:
        await client.post("/save", json=request)

    records = read_records(config)
    assert len(records) == 1
    assert records[0]["response"]["message"]["content"] == "hello test\nsaved"
