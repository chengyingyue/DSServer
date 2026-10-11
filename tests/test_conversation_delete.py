from __future__ import annotations

import json

import httpx

from .conftest import (
    build_app,
    chat_response,
    client_for,
    conversation_files,
    read_records,
    sequence_handler,
)


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _listing(client: httpx.AsyncClient) -> list[dict]:
    return (await client.get("/api/conversations")).json()


def _titles(conversations: list[dict]) -> set[str]:
    return {conversation["title"] for conversation in conversations}


async def test_delete_removes_records_file_and_index_entry(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        target = next(
            entry for entry in await _listing(client) if entry["title"] == "What is 2+2?"
        )
        response = await client.delete(
            f"/api/conversations/{target['key']}?branch={target['branch']}"
        )
        after = await _listing(client)

    assert response.status_code == 200
    assert response.json()["removed_records"] >= 1
    assert _titles(after) == {"Favourite colour?"}
    assert not (config.conversations_dir / target["filename"]).exists()
    assert target["name"] not in config.index_path.read_text(encoding="utf-8")
    remaining = json.dumps(read_records(config), ensure_ascii=False)
    assert "2+2" not in remaining


async def test_deletion_survives_a_restart(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        target = next(
            entry for entry in await _listing(client) if entry["title"] == "What is 2+2?"
        )
        await client.delete(f"/api/conversations/{target['key']}?branch={target['branch']}")

    build_app(config, sequence_handler([]))

    names = [path.name for path in conversation_files(config)]
    assert not any("2-2" in name for name in names)
    assert len(names) == 1


async def test_a_later_matching_chat_becomes_a_new_conversation(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("4 again")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        target = (await _listing(client))[0]
        await client.delete(f"/api/conversations/{target['key']}?branch={target['branch']}")
        await _capture(client, "What is 2+2?")
        after = await _listing(client)

    assert _titles(after) == {"What is 2+2?"}
    assert len(after) == 1
    assert after[0]["turns"] == 1


async def test_delete_reports_an_unknown_conversation(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.delete("/api/conversations/does-not-exist")

    assert response.status_code == 404
    assert "error" in response.json()


async def test_gui_offers_a_delete_action(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "removeConversation" in response.text
    assert "method: 'DELETE'" in response.text
