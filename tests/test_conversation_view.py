from __future__ import annotations

from .conftest import build_app, chat_response, client_for, sequence_handler


async def test_content_endpoint_returns_the_rendered_conversation(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    request = {
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "What is 2+2?"},
        ],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request)
        listing = (await client.get("/api/conversations")).json()
        entry = listing[0]
        response = await client.get(
            f"/api/conversations/{entry['key']}/content?branch={entry['branch']}"
        )

    assert response.status_code == 200
    body = response.json()
    assert "What is 2+2?" in body["content"]
    assert "### Assistant" in body["content"]
    assert body["name"] == "What is 2+2?"


async def test_unknown_conversation_content_errors_cleanly(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/api/conversations/does-not-exist/content")

    assert response.status_code == 404
    assert "error" in response.json()
