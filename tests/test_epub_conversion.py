from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from .conftest import build_app, client_for, sequence_handler, streaming_response

MIMETYPE = "application/epub+zip"


def _write_fixture(path: Path, *, marker: str = "Hello", title: str = "Fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chapter = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
<p>{marker} <em>world</em> and <strong>bold</strong></p>
<hr/>
</body>
</html>
"""
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Fixture</dc:title>
    <dc:identifier id="bookid">urn:uuid:fixture</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
"""
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, MIMETYPE)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter1.xhtml", chapter)


def _chapter(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("OEBPS/chapter1.xhtml").decode("utf-8")


def _names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


async def test_convert_single_inbox_file_produces_a_valid_tuned_epub(config):
    _write_fixture(config.epub_inbox_dir / "book.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/convert", json={"name": "book.epub"})

    assert response.status_code == 200
    assert response.json() == {"input": "book.epub", "output": "book.epub"}

    out = config.epub_out_dir / "book.epub"
    assert out.is_file()
    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert archive.read("mimetype") == MIMETYPE.encode()
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        chapter = archive.read("OEBPS/chapter1.xhtml").decode("utf-8")

    assert "---" in chapter
    assert "*world*" in chapter
    assert "<strong" in chapter
    assert "font-weight: bold" in chapter


async def test_scan_converts_every_inbox_file(config):
    _write_fixture(config.epub_inbox_dir / "one.epub", marker="One")
    _write_fixture(config.epub_inbox_dir / "two.epub", marker="Two")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/scan")

    body = response.json()
    assert response.status_code == 200
    assert [entry["input"] for entry in body["converted"]] == ["one.epub", "two.epub"]
    assert body["failed"] == []
    assert sorted(path.name for path in config.epub_out_dir.glob("*.epub")) == [
        "one.epub",
        "two.epub",
    ]
    assert "One" in _chapter(config.epub_out_dir / "one.epub")
    assert "Two" in _chapter(config.epub_out_dir / "two.epub")


async def test_malformed_input_returns_an_error_and_writes_no_output(config):
    config.epub_inbox_dir.mkdir(parents=True, exist_ok=True)
    (config.epub_inbox_dir / "broken.epub").write_text("not an epub", encoding="utf-8")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/convert", json={"name": "broken.epub"})

    assert 400 <= response.status_code < 600
    assert "error" in response.json()
    assert list(config.epub_out_dir.glob("*.epub")) == []


async def test_scan_reports_malformed_files_without_stopping(config):
    _write_fixture(config.epub_inbox_dir / "good.epub")
    config.epub_inbox_dir.mkdir(parents=True, exist_ok=True)
    (config.epub_inbox_dir / "bad.epub").write_text("nope", encoding="utf-8")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/scan")

    body = response.json()
    assert [entry["input"] for entry in body["converted"]] == ["good.epub"]
    assert [entry["input"] for entry in body["failed"]] == ["bad.epub"]
    assert (config.epub_out_dir / "good.epub").is_file()
    assert not (config.epub_out_dir / "bad.epub").exists()


async def test_repeated_conversion_does_not_corrupt_earlier_output(config):
    _write_fixture(config.epub_inbox_dir / "book.epub", marker="First")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        first = await client.post("/api/epub/convert", json={"name": "book.epub"})
        _write_fixture(config.epub_inbox_dir / "book.epub", marker="Second")
        second = await client.post("/api/epub/convert", json={"name": "book.epub"})

    assert first.json()["output"] == "book.epub"
    assert second.json()["output"] == "book-2.epub"
    first_out = config.epub_out_dir / "book.epub"
    second_out = config.epub_out_dir / "book-2.epub"
    assert _names(first_out)[0] == "mimetype"
    assert _names(second_out)[0] == "mimetype"
    assert "First" in _chapter(first_out)
    assert "Second" in _chapter(second_out)


async def test_convert_reports_a_missing_file(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/convert", json={"name": "nope.epub"})

    assert response.status_code == 404
    assert "error" in response.json()


async def test_convert_rejects_path_traversal_names(config):
    _write_fixture(config.epub_inbox_dir / "book.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/convert", json={"name": "../book.epub"})

    assert response.status_code == 400
    assert not (config.store_dir / "book.epub").exists()


async def test_api_epub_files_lists_inbox_and_out(config):
    _write_fixture(config.epub_inbox_dir / "one.epub")
    _write_fixture(config.epub_inbox_dir / "two.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        await client.post("/api/epub/convert", json={"name": "one.epub"})
        response = await client.get("/api/epub/files")

    body = response.json()
    assert body["inbox"] == ["one.epub", "two.epub"]
    assert body["out"] == ["one.epub"]


async def test_gui_page_offers_epub_conversion(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "/api/epub/convert" in response.text
    assert "/api/epub/scan" in response.text


async def test_epub_routes_are_not_forwarded_to_upstream(config):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return streaming_response(200, b"{}")

    app = build_app(config, handler)
    async with client_for(app) as client:
        await client.get("/api/epub/files")
        await client.post("/api/epub/scan")

    assert calls == []
