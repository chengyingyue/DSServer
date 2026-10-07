from __future__ import annotations

from .conftest import build_app, chat_response, client_for, sequence_handler


async def _one_conversation(client) -> dict:
    listing = (await client.get("/api/conversations")).json()
    return listing[0]


async def test_out_epub_can_be_downloaded(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions", json={"messages": [{"role": "user", "content": "Q"}]}
        )
        entry = await _one_conversation(client)
        build = await client.post(
            "/api/epub/build",
            json={"conversations": [{"key": entry["key"], "branch": entry["branch"]}]},
        )
        name = build.json()["output"]
        response = await client.get(f"/api/epub/out/{name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/epub+zip"
    assert response.content[:2] == b"PK"
    assert name in response.headers.get("content-disposition", "")


async def test_missing_out_epub_errors(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/api/epub/out/nope.epub")

    assert response.status_code == 404


async def test_work_copy_can_be_downloaded(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            json={"messages": [{"role": "user", "content": "What is 2+2?"}]},
        )
        entry = await _one_conversation(client)
        created = await client.post(
            "/api/epub/work",
            json={"conversations": [{"key": entry["key"], "branch": entry["branch"]}]},
        )
        work_id = created.json()["id"]
        response = await client.get(f"/api/epub/work/{work_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "What is 2+2?" in response.text
    assert "attachment" in response.headers.get("content-disposition", "")


async def test_missing_work_copy_download_errors(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get(f"/api/epub/work/{'0' * 32}/download")

    assert response.status_code == 404
