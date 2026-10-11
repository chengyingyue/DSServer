from __future__ import annotations

import httpx

from .conftest import build_app, chat_response, client_for, read_records, sequence_handler


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _listing(client: httpx.AsyncClient) -> list[dict]:
    return (await client.get("/api/conversations")).json()


async def _folders(client: httpx.AsyncClient) -> list[dict]:
    return (await client.get("/api/folders")).json()["folders"]


async def _create_folder(
    client: httpx.AsyncClient, name: str, parent: str = ""
) -> httpx.Response:
    return await client.post("/api/folders", json={"name": name, "parent": parent})


async def _assign(
    client: httpx.AsyncClient, conversation: dict, folder: str
) -> httpx.Response:
    return await client.post(
        f"/api/conversations/{conversation['key']}/folder",
        json={"branch": conversation["branch"], "folder": folder},
    )


async def test_create_rename_and_list_nested_folders(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        parent = await _create_folder(client, "Fanfic")
        assert parent.status_code == 200
        parent_id = parent.json()["id"]
        child = await _create_folder(client, "Ao3", parent_id)
        child_id = child.json()["id"]

        by_id = {folder["id"]: folder for folder in await _folders(client)}
        assert by_id[parent_id]["name"] == "Fanfic"
        assert by_id[parent_id]["parent"] == ""
        assert by_id[child_id]["parent"] == parent_id

        renamed = await client.patch(f"/api/folders/{child_id}", json={"name": "AO3"})
        assert renamed.status_code == 200
        assert {folder["id"]: folder["name"] for folder in await _folders(client)}[child_id] == "AO3"

    records = [record for record in read_records(config) if record["kind"] == "folder"]
    assert [record["op"] for record in records] == ["create", "create", "rename"]


async def test_assign_conversation_to_a_folder_and_back_to_root(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        assert conversation["folder"] == ""
        folder_id = (await _create_folder(client, "Notes")).json()["id"]

        assigned = await _assign(client, conversation, folder_id)
        assert assigned.status_code == 200
        assert assigned.json()["folder"] == folder_id
        assert (await _listing(client))[0]["folder"] == folder_id

        back = await _assign(client, conversation, "")
        assert back.json()["folder"] == ""
        assert (await _listing(client))[0]["folder"] == ""


async def test_deleting_a_folder_moves_its_conversations_to_the_parent(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        parent_id = (await _create_folder(client, "A")).json()["id"]
        child_id = (await _create_folder(client, "B", parent_id)).json()["id"]
        assert (await _assign(client, conversation, child_id)).status_code == 200

        deleted = await client.delete(f"/api/folders/{child_id}")
        assert deleted.status_code == 200
        remaining = {folder["id"] for folder in await _folders(client)}
        assert child_id not in remaining
        assert parent_id in remaining
        assert (await _listing(client))[0]["folder"] == parent_id


async def test_purging_a_conversation_removes_its_folder_assignment_record(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        folder_id = (await _create_folder(client, "Notes")).json()["id"]
        await _assign(client, conversation, folder_id)

        await client.delete(
            f"/api/conversations/{conversation['key']}?branch={conversation['branch']}"
        )

    records = read_records(config)
    assert not any(
        record["kind"] == "folder" and record.get("op") == "assign" for record in records
    )
    assert any(
        record["kind"] == "folder" and record.get("op") == "create" for record in records
    )


async def test_folder_endpoints_reject_bad_input(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        assert (await client.post("/api/folders", json={"name": "   "})).status_code == 400
        assert (
            await client.post("/api/folders", json={"name": "x", "parent": "missing"})
        ).status_code == 404
        assert (await client.patch("/api/folders/missing", json={"name": "x"})).status_code == 404
        assert (await client.delete("/api/folders/missing")).status_code == 404

        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        assert (await _assign(client, conversation, "missing")).status_code == 404
        missing = await client.post(
            "/api/conversations/does-not-exist/folder", json={"folder": ""}
        )
        assert missing.status_code == 404


async def test_gui_offers_conversation_folders(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "/api/folders" in response.text
    assert "Move to folder" in response.text
    assert "New folder" in response.text


async def test_conversations_default_to_normal_rendering(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        content = await client.get(
            f"/api/conversations/{conversation['key']}/content"
            f"?branch={conversation['branch']}"
        )

    assert content.json()["render"] == "normal"


async def test_a_folder_render_mode_overrides_its_conversations(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        folder_id = (await _create_folder(client, "Code")).json()["id"]
        await _assign(client, conversation, folder_id)

        set_render = await client.post(
            f"/api/folders/{folder_id}/render", json={"mode": "plain_code"}
        )
        assert set_render.status_code == 200
        assert set_render.json()["render"] == "plain_code"

        by_id = {folder["id"]: folder for folder in await _folders(client)}
        assert by_id[folder_id]["render"] == "plain_code"

        content = await client.get(
            f"/api/conversations/{conversation['key']}/content"
            f"?branch={conversation['branch']}"
        )
        assert content.json()["render"] == "plain_code"

    records = [
        record
        for record in read_records(config)
        if record["kind"] == "folder" and record.get("op") == "render"
    ]
    assert [record["mode"] for record in records] == ["plain_code"]


async def test_a_child_folder_inherits_its_parent_render_mode(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        parent_id = (await _create_folder(client, "Parent")).json()["id"]
        child_id = (await _create_folder(client, "Child", parent_id)).json()["id"]
        await client.post(f"/api/folders/{parent_id}/render", json={"mode": "plain_code"})
        await _assign(client, conversation, child_id)

        by_id = {folder["id"]: folder for folder in await _folders(client)}
        content = await client.get(
            f"/api/conversations/{conversation['key']}/content"
            f"?branch={conversation['branch']}"
        )

    assert by_id[child_id]["render"] == "plain_code"
    assert content.json()["render"] == "plain_code"


async def test_plain_code_mode_ignores_fences_and_renders_markdown(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "Hello there")
        conversation = (await _listing(client))[0]
        folder_id = (await _create_folder(client, "Code")).json()["id"]
        await _assign(client, conversation, folder_id)

        normal = await client.get(
            f"/api/conversations/{conversation['key']}/content"
            f"?branch={conversation['branch']}"
        )

        await client.post(f"/api/folders/{folder_id}/render", json={"mode": "plain_code"})
        plain = await client.get(
            f"/api/conversations/{conversation['key']}/content"
            f"?branch={conversation['branch']}"
        )

    assert normal.json()["render"] == "normal"
    assert "<pre>" in normal.json()["html"]
    assert plain.json()["render"] == "plain_code"
    assert "<pre>" not in plain.json()["html"]


async def test_render_endpoint_rejects_bad_input(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        folder_id = (await _create_folder(client, "Notes")).json()["id"]
        assert (
            await client.post(f"/api/folders/{folder_id}/render", json={"mode": "fancy"})
        ).status_code == 400
        assert (
            await client.post("/api/folders/missing/render", json={"mode": "plain_code"})
        ).status_code == 404
