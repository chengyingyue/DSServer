from __future__ import annotations

import os

import httpx

from dsserver.markdown import render_all

from .conftest import (
    build_app,
    chat_response,
    client_for,
    conversation_files,
    read_records,
    sequence_handler,
    streaming_response,
)


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _listing(client: httpx.AsyncClient) -> list[dict]:
    return (await client.get("/api/conversations")).json()


async def _rename(client: httpx.AsyncClient, conversation: dict, name: str) -> httpx.Response:
    return await client.post(
        f"/api/conversations/{conversation['key']}/rename",
        json={"name": name, "branch": conversation["branch"]},
    )


async def test_rename_changes_filename_index_and_persists_a_rename_record(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        conversation = (await _listing(client))[0]
        assert conversation["turns"] == 1
        response = await _rename(client, conversation, "My Maths Notes")
        assert response.status_code == 200

    assert [path.name for path in conversation_files(config)] == ["My Maths Notes.md"]
    assert "My Maths Notes.md" in config.index_path.read_text(encoding="utf-8")

    renames = [record for record in read_records(config) if record["kind"] == "rename"]
    assert len(renames) == 1
    assert renames[0]["key"] == conversation["key"]
    assert renames[0]["branch"] == conversation["branch"]
    assert renames[0]["name"] == "My Maths Notes"
    assert renames[0]["ts"]


async def test_full_rebuild_from_the_facts_store_preserves_the_chosen_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _rename(client, (await _listing(client))[0], "My Maths Notes")

    for path in conversation_files(config):
        path.unlink()
    config.index_path.unlink()

    render_all(config)

    assert [path.name for path in conversation_files(config)] == ["My Maths Notes.md"]


async def test_a_fresh_app_simulating_restart_preserves_the_chosen_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _rename(client, (await _listing(client))[0], "My Maths Notes")

    for path in conversation_files(config):
        path.unlink()
    config.index_path.unlink()

    build_app(config, sequence_handler([chat_response("unused")]))

    assert [path.name for path in conversation_files(config)] == ["My Maths Notes.md"]


async def test_multiple_renames_of_one_conversation_honour_the_latest(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _rename(client, (await _listing(client))[0], "First Choice")
        await _rename(client, (await _listing(client))[0], "Second Choice")

    assert [path.name for path in conversation_files(config)] == ["Second Choice.md"]
    renames = [record["name"] for record in read_records(config) if record["kind"] == "rename"]
    assert renames == ["First Choice", "Second Choice"]


async def test_rendering_never_overwrites_a_chosen_name_with_a_derived_one(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _rename(client, (await _listing(client))[0], "Keeper")
        await _capture(client, "Favourite colour?")

    render_all(config)

    names = [path.name for path in conversation_files(config)]
    assert "Keeper.md" in names
    assert len(names) == 2


async def test_a_conversation_without_a_rename_keeps_its_derived_filename(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")

    names = [path.name for path in conversation_files(config)]
    assert len(names) == 1
    assert names[0].endswith("-what-is-2-2.md")


async def test_api_list_reflects_the_chosen_name(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _rename(client, (await _listing(client))[0], "Readable Name")
        entry = (await _listing(client))[0]

    assert entry["name"] == "Readable Name"
    assert entry["filename"] == "Readable Name.md"
    assert entry["turns"] == 1
    assert entry["date"]


async def test_rename_addresses_the_exact_branch_conversation(config):
    app = build_app(
        config,
        sequence_handler([chat_response("4"), chat_response("4"), chat_response("6")]),
    )
    base_messages = [{"role": "user", "content": "What is 2+2?"}]
    async with client_for(app) as client:
        await client.post("/chat/completions", json={"messages": base_messages})
        await client.post("/chat/completions", json={"messages": list(base_messages)})
        await client.post(
            "/chat/completions",
            json={
                "messages": base_messages
                + [
                    {"role": "assistant", "content": "4"},
                    {"role": "user", "content": "And 3+3?"},
                ]
            },
        )
        listing = await _listing(client)
        assert len(listing) == 2
        assert len({entry["key"] for entry in listing}) == 1
        branch_one = next(entry for entry in listing if entry["branch"] == 1)
        response = await _rename(client, branch_one, "Forked")
        assert response.status_code == 200

    names = [path.name for path in conversation_files(config)]
    assert "Forked.md" in names
    assert any(name.endswith("-what-is-2-2.md") for name in names)
    assert not any("-b2" in name for name in names)


async def test_colliding_renames_are_disambiguated_deterministically(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        listing = await _listing(client)
        await _rename(client, listing[0], "Shared")
        await _rename(client, listing[1], "Shared")

    assert sorted(path.name for path in conversation_files(config)) == ["Shared-2.md", "Shared.md"]


async def test_rename_only_rebuilds_the_affected_conversation_file(config):
    old = 1_000_000.0
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        listing = await _listing(client)
        target = next(entry for entry in listing if entry["title"] == "Favourite colour?")
        untouched = next(entry for entry in listing if entry["title"] != "Favourite colour?")

        untouched_path = config.conversations_dir / untouched["filename"]
        content_before = untouched_path.read_text(encoding="utf-8")
        os.utime(untouched_path, (old, old))
        mtime_before = untouched_path.stat().st_mtime

        await _rename(client, target, "Renamed Colour")

    assert untouched_path.read_text(encoding="utf-8") == content_before
    assert untouched_path.stat().st_mtime == mtime_before
    assert (config.conversations_dir / "Renamed Colour.md").exists()


async def test_bridge_root_serves_the_gui_page(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/api/conversations" in response.text


async def test_local_gui_routes_are_not_forwarded_to_upstream(config):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.get("/")
        await client.get("/api/conversations")

    assert calls == []
