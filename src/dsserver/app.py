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

from .build import build_epub, build_epub_from_document
from .chat import ChatRequest, parse_chat_request, parse_chat_response
from .config import Config
from .epub import EpubError, convert_epub, list_epubs, unique_output
from .gui import INDEX_HTML
from .markdown import (
    Conversation,
    ConversationIndex,
    render_conversation,
    write_conversation,
    write_conversations_dir,
    write_index,
)
from .models import CHAT_KIND, OTHER_KIND, build_client_info, build_exchange, build_rename
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


def _conversation_summary(conversation: Conversation) -> dict[str, Any]:
    return {
        "key": conversation.key,
        "branch": conversation.branch,
        "name": conversation.name or conversation.title,
        "title": conversation.title,
        "date": conversation.date,
        "turns": len(conversation.turns),
        "filename": conversation.filename,
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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await client.aclose()

    app = FastAPI(lifespan=lifespan)
    app.state.config = config
    app.state.client = client
    app.state.store = store

    async def persist(record: dict[str, Any], markdown: bool) -> None:
        async with write_lock:
            await store.append(record)
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
        return HTMLResponse(INDEX_HTML)

    @app.get("/api/conversations")
    async def list_conversations() -> list[dict[str, Any]]:
        return [_conversation_summary(conversation) for conversation in index.conversations]

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
        return JSONResponse(_conversation_summary(conversation))

    @app.get("/api/conversations/{key}/content")
    async def conversation_content(key: str, branch: int = 0) -> Response:
        conversation = index.get(key, branch)
        if conversation is None:
            return JSONResponse({"error": "unknown conversation"}, status_code=404)
        return JSONResponse(
            {
                "name": conversation.name or conversation.title,
                "filename": conversation.filename,
                "content": render_conversation(conversation),
            }
        )

    @app.get("/api/epub/files")
    async def list_epub_files() -> dict[str, list[str]]:
        return {
            "inbox": list_epubs(config.epub_inbox_dir),
            "out": list_epubs(config.epub_out_dir),
        }

    @app.post("/api/epub/convert")
    async def convert_epub_file(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = _epub_filename(payload.get("name"))
        if name is None:
            return JSONResponse({"error": "name is required"}, status_code=400)
        source = config.epub_inbox_dir / name
        if not source.is_file():
            return JSONResponse({"error": f"file not found: {name}"}, status_code=404)
        try:
            destination = convert_epub(source, config.epub_out_dir)
        except EpubError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        return JSONResponse({"input": name, "output": destination.name})

    @app.post("/api/epub/upload")
    async def upload_epub(request: Request) -> Response:
        name = _epub_filename(request.query_params.get("name"))
        if name is None:
            return JSONResponse({"error": "name is required"}, status_code=400)
        if Path(name).suffix.lower() != ".epub":
            return JSONResponse({"error": "file must be an .epub"}, status_code=400)
        destination = unique_output(config.epub_inbox_dir, name)
        destination.write_bytes(await request.body())
        return JSONResponse({"name": destination.name})

    @app.post("/api/epub/scan")
    async def scan_epub_inbox() -> JSONResponse:
        converted: list[dict[str, str]] = []
        failed: list[dict[str, str]] = []
        for name in list_epubs(config.epub_inbox_dir):
            try:
                destination = convert_epub(config.epub_inbox_dir / name, config.epub_out_dir)
            except EpubError as error:
                failed.append({"input": name, "error": str(error)})
                continue
            converted.append({"input": name, "output": destination.name})
        return JSONResponse({"converted": converted, "failed": failed})

    @app.get("/api/epub/out/{name}")
    async def download_epub(name: str) -> Response:
        safe = _epub_filename(name)
        if safe is None:
            return JSONResponse({"error": "invalid name"}, status_code=400)
        path = config.epub_out_dir / safe
        if not path.is_file():
            return JSONResponse({"error": f"file not found: {safe}"}, status_code=404)
        return FileResponse(path, media_type="application/epub+zip", filename=safe)

    @app.post("/api/epub/work")
    async def create_work_copy(request: Request) -> Response:
        payload = await read_json_object(request)
        if isinstance(payload, JSONResponse):
            return payload

        selected = select_conversations(payload.get("conversations"))
        if isinstance(selected, JSONResponse):
            return selected

        content = "\n\n".join(render_conversation(conversation) for conversation in selected)
        work_id = work_store.create(content)
        return JSONResponse({"id": work_id, "content": content})

    @app.get("/api/epub/work/{work_id}")
    async def read_work_copy(work_id: str) -> Response:
        try:
            content = work_store.read(work_id)
        except WorkCopyError:
            return JSONResponse({"error": "unknown work copy"}, status_code=404)
        return JSONResponse({"id": work_id, "content": content})

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
            except WorkCopyError:
                return JSONResponse({"error": "unknown work copy"}, status_code=404)
            try:
                book = build_epub_from_document(markdown, config.epub_out_dir, title=title)
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
