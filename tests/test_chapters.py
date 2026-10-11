from __future__ import annotations

import zipfile

import httpx

from .conftest import build_app, chat_response, client_for, sequence_handler


async def _capture(client: httpx.AsyncClient, content: str) -> None:
    await client.post("/chat/completions", json={"messages": [{"role": "user", "content": content}]})


async def _work(client: httpx.AsyncClient, content: str) -> str:
    listing = (await client.get("/api/conversations")).json()
    selection = [{"key": entry["key"], "branch": entry["branch"]} for entry in listing]
    work_id = (await client.post("/api/epub/work", json={"conversations": selection})).json()["id"]
    await client.put(f"/api/epub/work/{work_id}", json={"content": content})
    return work_id


def _documents(path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return sorted(name for name in archive.namelist() if name.endswith(".xhtml"))


def _read(path, name: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name).decode("utf-8")


async def test_h1_headings_become_separate_chapters(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "seed")
        work_id = await _work(client, "# One\n\nFirst.\n\n# Two\n\nSecond.")
        response = await client.post("/api/epub/build", json={"work": work_id, "title": "Book"})

    assert response.status_code == 200
    documents = _documents(config.epub_out_dir / "Book.epub")
    assert len(documents) == 2
    assert "First." in _read(config.epub_out_dir / "Book.epub", "OEBPS/chapter1.xhtml")
    assert "Second." in _read(config.epub_out_dir / "Book.epub", "OEBPS/chapter2.xhtml")


async def test_the_chapter_separator_forces_a_break(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await _capture(client, "seed")
        work_id = await _work(client, "# Book\n\nBefore.\n<!-- chapter -->\nAfter.")
        response = await client.post("/api/epub/build", json={"work": work_id, "title": "Split"})

    assert response.status_code == 200
    documents = _documents(config.epub_out_dir / "Split.epub")
    assert len(documents) == 2
    assert "Before." in _read(config.epub_out_dir / "Split.epub", "OEBPS/chapter1.xhtml")
    assert "After." in _read(config.epub_out_dir / "Split.epub", "OEBPS/chapter2.xhtml")


async def test_the_editor_offers_an_outline_and_a_break_hint(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert "renderOutline" in response.text
    assert "&lt;!-- chapter --&gt;" in response.text
    assert "insertChapterBreak" not in response.text
