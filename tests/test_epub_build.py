from __future__ import annotations

import zipfile
from xml.etree import ElementTree

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


async def _build(
    client: httpx.AsyncClient,
    conversations: list[dict],
    title: str | None = None,
) -> httpx.Response:
    payload: dict = {"conversations": [_identity(conversation) for conversation in conversations]}
    if title is not None:
        payload["title"] = title
    return await client.post("/api/epub/build", json=payload)


def _document(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8")


async def test_build_from_two_conversations_produces_a_valid_epub(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        response = await _build(client, await _listing(client))

    assert response.status_code == 200
    output = response.json()["output"]

    path = config.epub_out_dir / output
    assert path.is_file()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert archive.read("mimetype") == MIMETYPE.encode()
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        documents = [name for name in names if name.endswith(".xhtml")]
        assert len(documents) >= 2
        combined = "\n".join(_document(archive, name) for name in documents)

    assert "What is 2+2?" in combined
    assert "Favourite colour?" in combined
    assert "<pre><code>" in combined


async def test_build_preserves_the_selected_order(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        listing = await _listing(client)
        colour = next(entry for entry in listing if entry["title"] == "Favourite colour?")
        maths = next(entry for entry in listing if entry["title"] == "What is 2+2?")
        response = await _build(client, [colour, maths])

    output = response.json()["output"]
    with zipfile.ZipFile(config.epub_out_dir / output) as archive:
        first = _document(archive, "OEBPS/chapter1.xhtml")
        second = _document(archive, "OEBPS/chapter2.xhtml")

    assert "Favourite colour?" in first
    assert "What is 2+2?" in second


async def test_build_uses_a_chosen_title_and_names_the_output(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        response = await _build(client, await _listing(client), title="My Reader Book")

    assert response.status_code == 200
    assert response.json() == {"output": "My Reader Book.epub", "title": "My Reader Book"}
    with zipfile.ZipFile(config.epub_out_dir / "My Reader Book.epub") as archive:
        opf = _document(archive, "OEBPS/content.opf")

    assert "My Reader Book" in opf


async def test_build_derives_a_sensible_title_when_none_is_given(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        response = await _build(client, await _listing(client))

    assert response.status_code == 200
    assert response.json()["title"] == "What is 2+2?"
    with zipfile.ZipFile(config.epub_out_dir / response.json()["output"]) as archive:
        assert "What is 2+2?" in _document(archive, "OEBPS/content.opf")


async def test_building_does_not_touch_the_facts_store_or_rendered_view(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("blue")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        await _capture(client, "Favourite colour?")
        listing = await _listing(client)

        log_before = config.log_path.read_bytes()
        names_before = sorted(path.name for path in conversation_files(config))
        contents_before = {
            path.name: path.read_text(encoding="utf-8") for path in conversation_files(config)
        }

        response = await _build(client, listing)

    assert response.status_code == 200
    assert config.log_path.read_bytes() == log_before
    assert sorted(path.name for path in conversation_files(config)) == names_before
    assert {
        path.name: path.read_text(encoding="utf-8") for path in conversation_files(config)
    } == contents_before
    assert [record["kind"] for record in read_records(config)].count("chat") == 2


async def test_build_requires_at_least_one_conversation(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/build", json={"conversations": []})

    assert response.status_code == 400
    assert "error" in response.json()
    assert list(config.epub_out_dir.glob("*.epub")) == []


async def test_build_reports_an_unknown_conversation(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post(
            "/api/epub/build",
            json={"conversations": [{"key": "does-not-exist", "branch": 0}]},
        )

    assert response.status_code == 404
    assert "error" in response.json()
    assert list(config.epub_out_dir.glob("*.epub")) == []


async def test_gui_offers_building_an_epub(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "/api/epub/build" in response.text
    assert "checkbox" in response.text


async def test_epub_build_route_is_not_forwarded_to_upstream(config):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.post("/api/epub/build", json={"conversations": []})

    assert calls == []


async def test_content_documents_declare_xhtml_and_utf8(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "What is 2+2?")
        response = await _build(client, await _listing(client))

    with zipfile.ZipFile(config.epub_out_dir / response.json()["output"]) as archive:
        documents = [name for name in archive.namelist() if name.endswith(".xhtml")]
        assert documents
        for name in documents:
            document = _document(archive, name)
            assert 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd' in document
            assert "charset=utf-8" in document
            ElementTree.fromstring(document)
        for name in ("OEBPS/content.opf", "OEBPS/toc.ncx", "META-INF/container.xml"):
            ElementTree.fromstring(archive.read(name))


async def test_build_removes_xml_invalid_control_characters(config):
    app = build_app(config, sequence_handler([chat_response("ok")]))
    async with client_for(app) as client:
        await _capture(client, "hello\u0000\u0007world")
        response = await _build(client, await _listing(client))

    with zipfile.ZipFile(config.epub_out_dir / response.json()["output"]) as archive:
        document = _document(archive, "OEBPS/chapter1.xhtml")
        opf = _document(archive, "OEBPS/content.opf")

    ElementTree.fromstring(document)
    ElementTree.fromstring(opf)
    assert "helloworld" in document
