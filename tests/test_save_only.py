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
    assert body["choices"][0]["message"]["content"] == "conversation saved"

    records = read_records(config)
    assert len(records) == 1
    assert records[0]["kind"] == "chat"
    assert records[0]["response"]["message"]["content"] == "conversation saved"
    assert records[0]["request"]["messages"] == request["messages"]


async def test_saved_conversation_appears_in_markdown(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)

    files = sorted(config.conversations_dir.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "conversation saved" in text
    assert "Remember this." in text


async def test_save_rejects_invalid_body(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/save", content=json.dumps({"foo": 1}))

    assert response.status_code == 400
