from __future__ import annotations

import zipfile

import httpx

from .conftest import (
    build_app,
    chat_response,
    client_for,
    conversation_files,
    read_records,
    sequence_handler,
    streaming_response,
)

MIMETYPE = "application/epub+zip"


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _listing(client: httpx.AsyncClient) -> list[dict]:
    return (await client.get("/api/conversations")).json()


def _identity(conversation: dict) -> dict:
    return {"key": conversation["key"], "branch": conversation["branch"]}


async def _create_work(client: httpx.AsyncClient, conversations: list[dict]) -> httpx.Response:
    return await client.post(
        "/api/epub/work",
        json={"conversations": [_identity(conversation) for conversation in conversations]},
    )


async def test_create_work_copy_from_a_conversation(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        response = await _create_work(client, await _listing(client))

    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert "What is 2+2?" in body["content"]
    assert (config.epub_work_dir / f"{body['id']}.md").is_file()
    assert [record["kind"] for record in read_records(config)].count("chat") == 1


async def test_edit_and_save_across_multiple_saves_then_get_returns_the_latest(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (await _create_work(client, await _listing(client))).json()["id"]

        first = await client.put(f"/api/epub/work/{work_id}", json={"content": "First draft"})
        second = await client.put(f"/api/epub/work/{work_id}", json={"content": "Second draft"})
        loaded = await client.get(f"/api/epub/work/{work_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json() == {"id": work_id, "content": "Second draft"}
    assert (config.epub_work_dir / f"{work_id}.md").read_text(encoding="utf-8") == "Second draft"


async def test_editing_a_work_copy_never_changes_the_facts_store_or_rendered_view(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (await _create_work(client, await _listing(client))).json()["id"]

        log_before = config.log_path.read_bytes()
        contents_before = {
            path.name: path.read_bytes() for path in conversation_files(config)
        }

        for draft in ("One edit", "Another edit", "Final edit"):
            response = await client.put(
                f"/api/epub/work/{work_id}", json={"content": draft}
            )
            assert response.status_code == 200

    assert config.log_path.read_bytes() == log_before
    assert {path.name: path.read_bytes() for path in conversation_files(config)} == contents_before
    assert [record["kind"] for record in read_records(config)].count("chat") == 1


async def test_build_from_a_work_copy_produces_a_valid_epub_reflecting_edits(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (await _create_work(client, await _listing(client))).json()["id"]
        await client.put(
            f"/api/epub/work/{work_id}",
            json={"content": "# Edited Book\n\nA hand-polished sentence."},
        )
        response = await client.post(
            "/api/epub/build", json={"work": work_id, "title": "Edited Book"}
        )

    assert response.status_code == 200
    assert response.json() == {"output": "Edited Book.epub", "title": "Edited Book"}

    path = config.epub_out_dir / "Edited Book.epub"
    assert path.is_file()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert archive.read("mimetype") == MIMETYPE.encode()
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        chapter = archive.read("OEBPS/chapter1.xhtml").decode("utf-8")

    assert "A hand-polished sentence." in chapter


async def test_discard_removes_the_work_copy(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        work_id = (await _create_work(client, await _listing(client))).json()["id"]
        path = config.epub_work_dir / f"{work_id}.md"
        assert path.is_file()

        response = await client.delete(f"/api/epub/work/{work_id}")
        after = await client.get(f"/api/epub/work/{work_id}")

    assert response.status_code == 200
    assert after.status_code == 404
    assert not path.exists()
    assert list(config.epub_work_dir.glob("*.md")) == []


async def test_unknown_work_ids_error_cleanly(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        loaded = await client.get("/api/epub/work/does-not-exist")
        saved = await client.put("/api/epub/work/does-not-exist", json={"content": "x"})
        discarded = await client.delete("/api/epub/work/does-not-exist")
        built = await client.post("/api/epub/build", json={"work": "does-not-exist"})

    for response in (loaded, saved, discarded, built):
        assert response.status_code == 404
        assert "error" in response.json()
    assert list(config.epub_out_dir.glob("*.epub")) == []


async def test_create_work_copy_requires_known_conversations(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        empty = await client.post("/api/epub/work", json={"conversations": []})
        unknown = await client.post(
            "/api/epub/work", json={"conversations": [{"key": "nope", "branch": 0}]}
        )

    assert empty.status_code == 400
    assert unknown.status_code == 404
    assert list(config.epub_work_dir.glob("*.md")) == []


async def test_work_routes_are_not_forwarded_to_upstream(config):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.post("/api/epub/work", json={"conversations": []})
        await client.get("/api/epub/work/missing")

    assert calls == []


async def test_gui_offers_work_copy_editing(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "/api/epub/work" in response.text
    assert "textarea" in response.text
