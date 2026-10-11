from __future__ import annotations

import httpx

from .conftest import build_app, chat_response, client_for, sequence_handler


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _selection(client: httpx.AsyncClient) -> list[dict]:
    listing = (await client.get("/api/conversations")).json()
    return [{"key": entry["key"], "branch": entry["branch"]} for entry in listing]


async def test_create_work_copy_with_a_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        response = await client.post(
            "/api/epub/work", json={"conversations": await _selection(client), "name": "My Book"}
        )
        listing = await client.get("/api/epub/work")

    assert response.status_code == 200
    assert response.json()["name"] == "My Book"
    assert [entry["name"] for entry in listing.json()["work"]] == ["My Book"]


async def test_default_name_comes_from_the_first_heading(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        response = await client.post(
            "/api/epub/work", json={"conversations": await _selection(client)}
        )

    assert response.json()["name"] == "What is 2+2?"


async def test_rename_a_work_copy(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (
            await client.post("/api/epub/work", json={"conversations": await _selection(client)})
        ).json()["id"]
        renamed = await client.patch(f"/api/epub/work/{work_id}", json={"name": "Renamed"})
        listing = await client.get("/api/epub/work")

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"
    assert [entry["name"] for entry in listing.json()["work"]] == ["Renamed"]


async def test_built_epub_uses_the_work_copy_name_as_its_title(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (
            await client.post(
                "/api/epub/work",
                json={"conversations": await _selection(client), "name": "My Book"},
            )
        ).json()["id"]
        response = await client.post("/api/epub/build", json={"work": work_id})

    assert response.status_code == 200
    assert response.json() == {"output": "My Book.epub", "title": "My Book"}
    assert (config.epub_out_dir / "My Book.epub").is_file()


async def test_build_title_can_override_the_work_copy_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (
            await client.post(
                "/api/epub/work",
                json={"conversations": await _selection(client), "name": "My Book"},
            )
        ).json()["id"]
        response = await client.post(
            "/api/epub/build", json={"work": work_id, "title": "Other Title"}
        )

    assert response.json() == {"output": "Other Title.epub", "title": "Other Title"}


async def test_discarding_removes_the_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (
            await client.post(
                "/api/epub/work",
                json={"conversations": await _selection(client), "name": "My Book"},
            )
        ).json()["id"]
        await client.delete(f"/api/epub/work/{work_id}")
        listing = await client.get("/api/epub/work")

    assert listing.json()["work"] == []
