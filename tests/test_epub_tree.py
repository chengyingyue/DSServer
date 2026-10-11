from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from dsserver import epub

from .conftest import build_app, client_for, sequence_handler

MIMETYPE = "application/epub+zip"


def _write_fixture(path: Path, *, marker: str = "Hello") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chapter = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title></head>'
        f"<body><p>{marker}</p></body></html>\n"
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>\n'
    )
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">'
        "<metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><dc:title>t</dc:title>"
        '<dc:identifier id="bookid">urn:uuid:x</dc:identifier></metadata>'
        '<manifest><item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>'
        '</manifest><spine><itemref idref="c1"/></spine></package>\n'
    )
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, MIMETYPE)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter1.xhtml", chapter)


def _paths(node: dict) -> list[str]:
    found = [node["path"]]
    for child in node.get("children", []):
        found.extend(_paths(child))
    return found


async def test_tree_reflects_nested_folders(config):
    _write_fixture(config.epub_inbox_dir / "ao3" / "P" / "story.epub")
    _write_fixture(config.epub_out_dir / "done.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/api/epub/tree")

    body = response.json()
    assert response.status_code == 200
    paths = set()
    for root in body["roots"]:
        paths.update(_paths(root))
    assert "inbox/ao3/P/story.epub" in paths
    assert "out/done.epub" in paths


async def test_tree_preserves_non_ascii_names(config):
    (config.epub_inbox_dir / "中文").mkdir(parents=True, exist_ok=True)
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/api/epub/tree")

    paths = {path for root in response.json()["roots"] for path in _paths(root)}
    assert "inbox/中文" in paths


async def test_folder_create_rename_and_recursive_delete(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        created = await client.post("/api/epub/folder", json={"path": "inbox/ao3"})
        nested = await client.post("/api/epub/folder", json={"path": "inbox/ao3/sub"})
        _write_fixture(config.epub_inbox_dir / "ao3" / "sub" / "x.epub")
        assert (config.epub_inbox_dir / "ao3" / "sub").is_dir()
        renamed = await client.post(
            "/api/epub/folder/rename",
            json={"from": "inbox/ao3/sub", "to": "inbox/ao3/sub2"},
        )
        assert (config.epub_inbox_dir / "ao3" / "sub2").is_dir()
        deleted = await client.request("DELETE", "/api/epub/folder?path=inbox/ao3")

    assert created.status_code == 200
    assert nested.status_code == 200
    assert renamed.status_code == 200
    assert deleted.status_code == 200
    assert not (config.epub_inbox_dir / "ao3").exists()


async def test_folder_actions_refuse_unsafe_or_root_paths(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        traversal = await client.post("/api/epub/folder", json={"path": "inbox/../escape"})
        root_delete = await client.request("DELETE", "/api/epub/folder?path=inbox")
        work = await client.post("/api/epub/folder", json={"path": "work/nope"})

    assert traversal.status_code == 400
    assert root_delete.status_code == 400
    assert work.status_code == 400
    assert not (config.store_dir / "escape").exists()
    assert config.epub_inbox_dir.is_dir()


async def test_file_move_within_root_and_cross_root_refusal(config):
    _write_fixture(config.epub_inbox_dir / "a.epub")
    (config.epub_inbox_dir / "sub").mkdir(parents=True, exist_ok=True)
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        moved = await client.post(
            "/api/epub/move", json={"from": "inbox/a.epub", "to": "inbox/sub/a.epub"}
        )
        cross = await client.post(
            "/api/epub/move", json={"from": "inbox/sub/a.epub", "to": "out/a.epub"}
        )

    assert moved.status_code == 200
    assert (config.epub_inbox_dir / "sub" / "a.epub").is_file()
    assert cross.status_code == 400
    assert (config.epub_inbox_dir / "sub" / "a.epub").is_file()


async def test_file_delete(config):
    _write_fixture(config.epub_inbox_dir / "a.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.request("DELETE", "/api/epub/file?path=inbox/a.epub")

    assert response.status_code == 200
    assert not (config.epub_inbox_dir / "a.epub").exists()


async def test_recursive_convert_mirrors_the_source_layout(config):
    _write_fixture(config.epub_inbox_dir / "ao3" / "x.epub", marker="Nested")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.post("/api/epub/convert", json={"path": "inbox/ao3"})

    body = response.json()
    assert response.status_code == 200
    assert body["converted"] == [{"input": "ao3/x.epub", "output": "ao3/x.epub"}]
    assert body["failed"] == []
    out = config.epub_out_dir / "ao3" / "x.epub"
    assert out.is_file()
    with zipfile.ZipFile(out) as archive:
        assert archive.namelist()[0] == "mimetype"


async def test_download_any_out_file_by_path(config):
    _write_fixture(config.epub_out_dir / "ao3" / "x.epub")
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/api/epub/file?path=out/ao3/x.epub")
        unsafe = await client.get("/api/epub/file?path=out/../../x.epub")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/epub+zip"
    assert unsafe.status_code == 400


async def test_the_gui_offers_folder_download(config):
    app = build_app(config, sequence_handler([]))
    async with client_for(app) as client:
        response = await client.get("/")

    assert "downloadFolder" in response.text
    assert "folderEpubs" in response.text


def test_convert_path_accepts_a_relative_root(tmp_path, monkeypatch):
    _write_fixture(tmp_path / "data" / "epub" / "inbox" / "x.epub")
    monkeypatch.chdir(tmp_path)

    result = epub.convert_path("data/epub", "inbox/x.epub")

    assert result == {"kind": "file", "input": "x.epub", "output": "x.epub"}
    assert (tmp_path / "data" / "epub" / "out" / "x.epub").is_file()
