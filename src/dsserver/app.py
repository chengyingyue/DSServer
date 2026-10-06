from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse

from .chat import ChatRequest, parse_chat_request, parse_chat_response
from .config import Config
from .markdown import write_markdown
from .models import CHAT_KIND, OTHER_KIND, build_client_info, build_exchange
from .store import Store
from .stream import StreamResult, tee_sse

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
                write_markdown(config, store.records)

    async def record_other(request: Request, status: int, latency_ms: int) -> None:
        record = build_exchange(
            OTHER_KIND,
            build_client_info(request.headers, config.header_whitelist),
            {"method": request.method, "path": request.url.path},
            {"status": status},
            {"latency_ms": latency_ms, "upstream": upstream_host},
        )
        await persist(record.to_dict(), markdown=False)

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
