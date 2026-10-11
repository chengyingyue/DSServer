from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse

from .build import build_epub, build_epub_from_document, render_markdown_html
from .chat import ChatRequest, parse_chat_request, parse_chat_response
from .config import Config
from .epub import (
    EpubError,
    EpubPathError,
    convert_path,
    create_folder,
    delete_file,
    delete_folder,
    epub_tree,
    list_epubs,
    move_file,
    rename_folder,
    resolve_epub_path,
    unique_output,
)
from .gui import INDEX_HTML
from .markdown import (
    Conversation,
    ConversationIndex,
    render_conversation,
    smart_zone_limit_label,
    smart_zone_percent,
    write_conversation,
    write_conversations_dir,
    write_index,
)
from .models import (
    CHAT_KIND,
    OTHER_KIND,
    RENDER_MODES,
    RENDER_PLAIN_CODE,
    build_client_info,
    build_exchange,
    build_folder_assign,
    build_folder_create,
    build_folder_delete,
    build_folder_rename,
    build_folder_render,
    build_rename,
    new_id,
)
from .store import Store
from .stream import StreamResult, tee_sse
from .work import WorkCopyError, WorkStore

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

UPSTREAM_TIMEOUT = httpx.Timeout(600.0, connect=30.0)

SAVE_PATH = "/save"
SAVE_MARKER = "conversation saved"


def _forward_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in HOP_BY_HOP_HEADERS or lowered == "accept-encoding":
            continue
        forwarded[name] = value
    return forwarded


def _forward_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {name: value for name, value in headers.items() if name.lower() not in HOP_BY_HOP_HEADERS}


def _chat_response_dict(
    status: int,
    usage: dict[str, Any] | None,
    finish_reason: str | None,
    message: dict[str, Any],
) -> dict[str, Any]:
    return {"status": status, "usage": usage, "finish_reason": finish_reason, "message": message}


def _conversation_summary(conversation: Conversation, folder: str) -> dict[str, Any]:
    return {
        "key": conversation.key,
        "branch": conversation.branch,
        "name": conversation.name or conversation.title,
        "title": conversation.title,
        "date": conversation.date,
        "turns": len(conversation.turns),
        "filename": conversation.filename,
        "folder": folder,
    }


def _epub_filename(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()
    if not name or name in (".", "..") or Path(name).name != name:
        return None
    return name


async def read_json_object(request: Request) -> dict[str, Any] | JSONResponse:
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)
    return payload


def _passthrough(upstream_response: httpx.Response) -> StreamingResponse:
    async def relay() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_response.aiter_raw():
                yield chunk
        finally:
            await upstream_response.aclose()

    return StreamingResponse(
        relay(),
        status_code=upstream_response.status_code,
        headers=_forward_response_headers(upstream_response.headers),
    )


async def _read_raw(upstream_response: httpx.Response) -> bytes:
    raw = b"".join([chunk async for chunk in upstream_response.aiter_raw()])
    await upstream_response.aclose()
    return raw


def create_app(
    config: Config,
    upstream_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    client = httpx.AsyncClient(
        base_url=config.upstream_base_url,
        transport=upstream_transport,
        timeout=UPSTREAM_TIMEOUT,
        headers={"accept-encoding": "identity"},
    )
    store = Store(config.log_path)
    index = ConversationIndex.from_records(store.records)
    write_conversations_dir(config, index.conversations)
    write_index(config, index.conversations)
    config.epub_inbox_dir.mkdir(parents=True, exist_ok=True)
    config.epub_out_dir.mkdir(parents=True, exist_ok=True)
    config.epub_work_dir.mkdir(parents=True, exist_ok=True)
    work_store = WorkStore(config.epub_work_dir)
    write_lock = asyncio.Lock()
    upstream_host = urlsplit(config.upstream_base_url).netloc

    def rebuild_index() -> None:
        nonlocal index
        index = ConversationIndex.from_records(store.records)
        write_conversations_dir(config, index.conversations)
        write_index(config, index.conversations)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await client.aclose()

    app = FastAPI(lifespan=lifespan)
    app.state.config = config
    app.state.client = client
    app.state.store = store

    def log_chat_tokens(record: dict[str, Any]) -> None:
        if record.get("kind") != CHAT_KIND:
            return
        response = record.get("response") or {}
        usage = response.get("usage") or {}
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        total = usage.get("total_tokens")
        if prompt is None and completion is None and total is None:
            return
        model = (record.get("request") or {}).get("model") or "?"
        latency = (record.get("meta") or {}).get("latency_ms")
        parts = [f"[chat] {model}"]
        if prompt is not None:
            parts.append(f"prompt={prompt:,}")
        if completion is not None:
            parts.append(f"completion={completion:,}")
        if total is not None:
            parts.append(f"total={total:,}")
        percent = smart_zone_percent(prompt, config.smart_zone_tokens)
        if percent is not None:
            limit = smart_zone_limit_label(config.smart_zone_tokens)
            parts.append(f"ctx={prompt:,}/{limit} ({percent}%)")
        if latency is not None:
            parts.append(f"{latency}ms")
        print(" · ".join(parts), flush=True)

    async def persist(record: dict[str, Any], markdown: bool) -> None:
        async with write_lock:
            await store.append(record)
            log_chat_tokens(record)
            if markdown:
                conversation = index.apply(record)
                if conversation is not None:
                    write_conversation(config, conversation)
                write_index(config, index.conversations)

    async def record_other(request: Request, status: int, latency_ms: int) -> None:
        record = build_exchange(
            OTHER_KIND,
            build_client_info(request.headers, config.header_whitelist),
            {"method": request.method, "path": request.url.path},
            {"status": status},
            {"latency_ms": latency_ms, "upstream": upstream_host},
        )
        await persist(record.to_dict(), markdown=False)

    def select_conversations(raw_items: Any) -> list[Conversation] | JSONResponse:
        if not isinstance(raw_items, list) or not raw_items:
            return JSONResponse({"error": "conversations is required"}, status_code=400)
        selected: list[Conversation] = []
        for item in raw_items:
            if not isinstance(item, dict):
                return JSONResponse({"error": "invalid conversation entry"}, status_code=400)
            key = item.get("key")
            if not isinstance(key, str):
                return JSONResponse({"error": "invalid conversation entry"}, status_code=400)
            try:
                branch = int(item.get("branch", 0) or 0)
            except (TypeError, ValueError):
                return JSONResponse({"error": "branch must be an integer"}, status_code=400)
            conversation = index.get(key, branch)
            if conversation is None:
                return JSONResponse({"error": "unknown conversation"}, status_code=404)
            selected.append(conversation)
        return selected

    @app.get("/", response_class=HTMLResponse)
    async def gui_root() -> HTMLResponse:
        return HTMLResponse(INDEX_HTML, headers={"Cache-Control": "no-cache"})

    @app.get("/api/conversations")
    async def list_conversations() -> list[dict[str, Any]]:
        return [
            _conversation_summary(conversation, index.folder_of(conversation))
            for conversation in index.conversations
        ]

    @app.post("/api/conversations/{key}/rename")
    async def rename_conversation(key: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        try:
            branch = int(payload.get("branch", 0) or 0)
        except (TypeError, ValueError):
            return JSONResponse({"error": "branch must be an integer"}, status_code=400)

        trimmed = name.strip()
        async with write_lock:
            before = index.get(key, branch)
            if before is None:
                return JSONResponse({"error": "unknown conversation"}, status_code=404)
            if index.name_in_use(trimmed, before):
                return JSONResponse(
                    {"error": f'name "{trimmed}" is already used by another conversation'},
                    status_code=409,
                )
            old_filename = before.filename
            record = build_rename(key, branch, trimmed)
            await store.append(record)
            conversation = index.apply(record)
            if conversation is None:
                return JSONResponse({"error": "rename could not be applied"}, status_code=409)
            write_conversation(config, conversation)
            if old_filename != conversation.filename:
                stale = config.conversations_dir / old_filename
                stale.unlink(missing_ok=True)
            write_index(config, index.conversations)
        return JSONResponse(_conversation_summary(conversation, index.folder_of(conversation)))

    @app.get("/api/conversations/{key}/content")
    async def conversation_content(key: str, branch: int = 0) -> Response:
        conversation = index.get(key, branch)
        if conversation is None:
            return JSONResponse({"error": "unknown conversation"}, status_code=404)
        markdown = render_conversation(conversation, config.smart_zone_tokens)
        mode = index.render_mode_of(conversation)
        return JSONResponse(
            {
                "name": conversation.name or conversation.title,
                "filename": conversation.filename,
                "content": markdown,
                "html": render_markdown_html(markdown, plain_code=(mode == RENDER_PLAIN_CODE)),
                "render": mode,
            }
        )

    @app.delete("/api/conversations/{key}")
    async def purge_conversation(key: str, branch: int = 0) -> Response:
        async with write_lock:
            conversation = index.get(key, branch)
            if conversation is None:
                return JSONResponse({"error": "unknown conversation"}, status_code=404)
            removed = await store.purge(set(conversation.record_ids))
            rebuild_index()
        return JSONResponse({"deleted": True, "removed_records": removed})

    @app.get("/api/folders")
    async def list_folders() -> JSONResponse:
        return JSONResponse({"folders": index.folders()})

    @app.post("/api/folders")
    async def create_conversation_folder(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        parent = payload.get("parent") or ""
        if not isinstance(parent, str):
            return JSONResponse({"error": "parent must be a string"}, status_code=400)
        if not index.has_folder(parent):
            return JSONResponse({"error": "unknown parent folder"}, status_code=404)
        folder_id = new_id()
        record = build_folder_create(folder_id, name.strip(), parent)
        async with write_lock:
            await store.append(record)
            index.apply(record)
        return JSONResponse({"id": folder_id, "name": name.strip(), "parent": parent})

    @app.patch("/api/folders/{folder_id}")
    async def rename_conversation_folder(folder_id: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        if not index.has_folder(folder_id):
            return JSONResponse({"error": "unknown folder"}, status_code=404)
        record = build_folder_rename(folder_id, name.strip())
        async with write_lock:
            await store.append(record)
            index.apply(record)
        return JSONResponse({"id": folder_id, "name": name.strip()})

    @app.delete("/api/folders/{folder_id}")
    async def delete_conversation_folder(folder_id: str) -> Response:
        if not index.has_folder(folder_id):
            return JSONResponse({"error": "unknown folder"}, status_code=404)
        record = build_folder_delete(folder_id)
        async with write_lock:
            await store.append(record)
            index.apply(record)
        return JSONResponse({"id": folder_id, "deleted": True})

    @app.post("/api/folders/{folder_id}/render")
    async def set_conversation_folder_render(folder_id: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        mode = payload.get("mode")
        if mode not in RENDER_MODES:
            return JSONResponse({"error": "unknown render mode"}, status_code=400)
        if not index.has_folder(folder_id):
            return JSONResponse({"error": "unknown folder"}, status_code=404)
        record = build_folder_render(folder_id, mode)
        async with write_lock:
            await store.append(record)
            index.apply(record)
        return JSONResponse({"id": folder_id, "render": mode})

    @app.post("/api/conversations/{key}/folder")
    async def assign_conversation_folder(key: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        try:
            branch = int(payload.get("branch", 0) or 0)
        except (TypeError, ValueError):
            return JSONResponse({"error": "branch must be an integer"}, status_code=400)
        folder = payload.get("folder") or ""
        if not isinstance(folder, str):
            return JSONResponse({"error": "folder must be a string"}, status_code=400)
        conversation = index.get(key, branch)
        if conversation is None:
            return JSONResponse({"error": "unknown conversation"}, status_code=404)
        if not index.has_folder(folder):
            return JSONResponse({"error": "unknown folder"}, status_code=404)
        record = build_folder_assign(folder, key, branch)
        async with write_lock:
            await store.append(record)
            index.apply(record)
        return JSONResponse(_conversation_summary(conversation, index.folder_of(conversation)))

    @app.get("/api/epub/files")
    async def list_epub_files() -> dict[str, list[str]]:
        return {
            "inbox": list_epubs(config.epub_inbox_dir),
            "out": list_epubs(config.epub_out_dir),
        }

    @app.get("/api/epub/tree")
    async def epub_library_tree() -> Response:
        roots = epub_tree(config.epub_dir)
        names = {entry["id"]: entry["name"] for entry in work_store.list()}
        for root in roots:
            if root.get("name") != "work":
                continue
            for child in root.get("children", []):
                work_id = Path(child["path"]).stem
                if work_id in names:
                    child["name"] = names[work_id]
        return JSONResponse({"roots": roots})

    @app.post("/api/epub/folder")
    async def create_epub_folder(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        path = payload.get("path")
        if not isinstance(path, str) or not path.strip():
            return JSONResponse({"error": "path is required"}, status_code=400)
        try:
            create_folder(config.epub_dir, path)
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        return JSONResponse({"created": path})

    @app.post("/api/epub/folder/rename")
    async def rename_epub_folder(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        source = payload.get("from")
        target = payload.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            return JSONResponse({"error": "from and to are required"}, status_code=400)
        try:
            rename_folder(config.epub_dir, source, target)
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        return JSONResponse({"renamed": target})

    @app.delete("/api/epub/folder")
    async def delete_epub_folder(path: str) -> Response:
        try:
            delete_folder(config.epub_dir, path)
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        return JSONResponse({"deleted": path})

    @app.post("/api/epub/move")
    async def move_epub_file(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        source = payload.get("from")
        target = payload.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            return JSONResponse({"error": "from and to are required"}, status_code=400)
        try:
            move_file(config.epub_dir, source, target)
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        return JSONResponse({"moved": target})

    @app.delete("/api/epub/file")
    async def delete_epub_file(path: str) -> Response:
        try:
            delete_file(config.epub_dir, path)
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        return JSONResponse({"deleted": path})

    @app.post("/api/epub/convert")
    async def convert_epub_file(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        rel = payload.get("path")
        if rel is None:
            name = payload.get("name")
            if name is None:
                return JSONResponse({"error": "path is required"}, status_code=400)
            rel = "inbox/" + str(name)
        try:
            source = resolve_epub_path(config.epub_dir, rel, roots=("inbox",))
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        if not source.exists():
            return JSONResponse({"error": f"path not found: {rel}"}, status_code=404)
        try:
            result = convert_path(config.epub_dir, rel)
        except EpubError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        if result["kind"] == "file":
            return JSONResponse({"input": result["input"], "output": result["output"]})
        return JSONResponse({"converted": result["converted"], "failed": result["failed"]})

    @app.post("/api/epub/upload")
    async def upload_epub(request: Request) -> Response:
        name = _epub_filename(request.query_params.get("name"))
        if name is None:
            return JSONResponse({"error": "name is required"}, status_code=400)
        if Path(name).suffix.lower() != ".epub":
            return JSONResponse({"error": "file must be an .epub"}, status_code=400)
        directory = config.epub_inbox_dir
        target_dir = request.query_params.get("dir")
        if target_dir:
            try:
                directory = resolve_epub_path(config.epub_dir, target_dir, roots=("inbox",))
            except EpubPathError as error:
                return JSONResponse({"error": str(error)}, status_code=400)
            if not directory.is_dir():
                return JSONResponse({"error": f"folder not found: {target_dir}"}, status_code=404)
        directory.mkdir(parents=True, exist_ok=True)
        destination = unique_output(directory, name)
        destination.write_bytes(await request.body())
        return JSONResponse({"name": destination.name})

    @app.post("/api/epub/scan")
    async def scan_epub_inbox() -> JSONResponse:
        try:
            result = convert_path(config.epub_dir, "inbox")
        except EpubError as error:
            return JSONResponse(
                {"converted": [], "failed": [{"input": "inbox", "error": str(error)}]}
            )
        return JSONResponse({"converted": result["converted"], "failed": result["failed"]})

    @app.get("/api/epub/file")
    async def download_epub_file(path: str) -> Response:
        try:
            target = resolve_epub_path(config.epub_dir, path, roots=("inbox", "out"))
        except EpubPathError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        if not target.is_file():
            return JSONResponse({"error": f"file not found: {path}"}, status_code=404)
        return FileResponse(target, media_type="application/epub+zip", filename=target.name)

    @app.get("/api/epub/out/{name}")
    async def download_epub(name: str) -> Response:
        safe = _epub_filename(name)
        if safe is None:
            return JSONResponse({"error": "invalid name"}, status_code=400)
        path = config.epub_out_dir / safe
        if not path.is_file():
            return JSONResponse({"error": f"file not found: {safe}"}, status_code=404)
        return FileResponse(path, media_type="application/epub+zip", filename=safe)

    @app.get("/api/epub/work")
    async def list_work_copies() -> Response:
        return JSONResponse({"work": work_store.list()})

    @app.post("/api/epub/work")
    async def create_work_copy(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload

        selected = select_conversations(payload.get("conversations"))
        if isinstance(selected, JSONResponse):
            return selected

        name = payload.get("name")
        if name is not None and not isinstance(name, str):
            return JSONResponse({"error": "name must be a string"}, status_code=400)

        content = "\n\n".join(
            render_conversation(conversation, config.smart_zone_tokens) for conversation in selected
        )
        work_id = work_store.create(content, name)
        return JSONResponse(
            {"id": work_id, "name": work_store.name(work_id), "content": content}
        )

    @app.get("/api/epub/work/{work_id}")
    async def read_work_copy(work_id: str) -> Response:
        try:
            content = work_store.read(work_id)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        return JSONResponse({"id": work_id, "content": content})

    @app.patch("/api/epub/work/{work_id}")
    async def rename_work_copy(work_id: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        try:
            work_store.rename(work_id, name)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        return JSONResponse({"id": work_id, "name": name.strip()})

    @app.get("/api/epub/work/{work_id}/download")
    async def download_work_copy(work_id: str) -> Response:
        try:
            content = work_store.read(work_id)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        headers = {"Content-Disposition": f'attachment; filename="{work_id}.md"'}
        return Response(content=content, media_type="text/markdown", headers=headers)

    @app.put("/api/epub/work/{work_id}")
    async def save_work_copy(work_id: str, request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        content = payload.get("content")
        if not isinstance(content, str):
            return JSONResponse({"error": "content is required"}, status_code=400)
        try:
            work_store.save(work_id, content)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        return JSONResponse({"id": work_id, "content": content})

    @app.delete("/api/epub/work/{work_id}")
    async def discard_work_copy(work_id: str) -> Response:
        try:
            work_store.discard(work_id)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        return JSONResponse({"id": work_id, "discarded": True})

    @app.post("/api/epub/build")
    async def build_epub_book(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload

        title = payload.get("title")
        if title is not None and not isinstance(title, str):
            return JSONResponse({"error": "title must be a string"}, status_code=400)

        work_id = payload.get("work")
        if work_id is not None:
            if not isinstance(work_id, str):
                return JSONResponse({"error": "work must be a string"}, status_code=400)
            try:
                markdown = work_store.read(work_id)
                work_title = title.strip() if isinstance(title, str) and title.strip() else work_store.name(work_id)
            except WorkCopyError:
                return JSONResponse({"error": "unknown work copy"}, status_code=404)
            try:
                book = build_epub_from_document(markdown, config.epub_out_dir, title=work_title)
            except EpubError as error:
                return JSONResponse({"error": str(error)}, status_code=422)
            return JSONResponse({"output": book.path.name, "title": book.title})

        selected = select_conversations(payload.get("conversations"))
        if isinstance(selected, JSONResponse):
            return selected

        try:
            book = build_epub(selected, config.epub_out_dir, title=title)
        except EpubError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        return JSONResponse({"output": book.path.name, "title": book.title})

    @app.post(SAVE_PATH)
    async def save_only(request: Request) -> Response:
        body = await request.body()
        try:
            chat_request = parse_chat_request(body)
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid chat request"}, status_code=400)

        message = {"role": "assistant", "content": SAVE_MARKER}
        record = build_exchange(
            CHAT_KIND,
            build_client_info(request.headers, config.header_whitelist),
            chat_request.to_request_dict(request.url.path),
            _chat_response_dict(200, None, "stop", message),
            {"upstream": None},
        )
        await persist(record.to_dict(), markdown=True)

        completion = {
            "id": record.id,
            "object": "chat.completion",
            "model": chat_request.model or "",
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": None,
        }
        return JSONResponse(completion)

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def proxy(full_path: str, request: Request) -> Response:
        body = await request.body()
        query = request.url.query
        target = f"/{full_path}"
        if query:
            target = f"{target}?{query}"

        is_deep = request.method == "POST" and request.url.path in config.deep_paths
        chat_request: ChatRequest | None = None
        if is_deep:
            try:
                chat_request = parse_chat_request(body)
            except (ValueError, TypeError):
                chat_request = None

        started = time.perf_counter()
        upstream_request = client.build_request(
            request.method,
            target,
            headers=_forward_request_headers(request.headers),
            content=body,
        )
        upstream_response = await client.send(upstream_request, stream=True)
        status = upstream_response.status_code
        latency_ms = lambda: int((time.perf_counter() - started) * 1000)

        if chat_request is not None and 200 <= status < 300 and not chat_request.stream:
            raw = await _read_raw(upstream_response)
            headers = _forward_response_headers(upstream_response.headers)
            elapsed = latency_ms()
            try:
                message, usage, finish_reason = parse_chat_response(raw)
            except (ValueError, TypeError):
                await record_other(request, status, elapsed)
                return Response(content=raw, status_code=status, headers=headers)
            record = build_exchange(
                CHAT_KIND,
                build_client_info(request.headers, config.header_whitelist),
                chat_request.to_request_dict(request.url.path),
                _chat_response_dict(status, usage, finish_reason, message),
                {"latency_ms": elapsed, "upstream": upstream_host},
            )
            await persist(record.to_dict(), markdown=True)
            return Response(content=raw, status_code=status, headers=headers)

        if chat_request is not None and 200 <= status < 300 and chat_request.stream:
            client_info = build_client_info(request.headers, config.header_whitelist)
            request_dict = chat_request.to_request_dict(request.url.path)
            response_headers = _forward_response_headers(upstream_response.headers)

            async def on_complete(result: StreamResult) -> None:
                message: dict[str, Any] = {"role": "assistant", "content": result.content}
                if result.reasoning_content:
                    message["reasoning_content"] = result.reasoning_content
                if result.tool_calls:
                    message["tool_calls"] = result.tool_calls
                record = build_exchange(
                    CHAT_KIND,
                    client_info,
                    request_dict,
                    _chat_response_dict(status, result.usage, result.finish_reason, message),
                    {"latency_ms": latency_ms(), "upstream": upstream_host},
                    raw_sse=result.raw_sse if config.keep_raw_sse else None,
                )
                await persist(record.to_dict(), markdown=True)

            return StreamingResponse(
                tee_sse(upstream_response, on_complete),
                status_code=status,
                headers=response_headers,
            )

        await record_other(request, status, latency_ms())
        return _passthrough(upstream_response)

    return app
