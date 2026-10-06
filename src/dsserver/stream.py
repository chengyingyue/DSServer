from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx


@dataclass
class StreamResult:
    content: str
    reasoning_content: str
    tool_calls: list[dict[str, Any]]
    usage: dict[str, Any] | None
    finish_reason: str | None
    raw_sse: str


class SSEAccumulator:
    def __init__(self) -> None:
        self._content: list[str] = []
        self._reasoning: list[str] = []
        self._tool_calls: dict[int, dict[str, Any]] = {}
        self._usage: dict[str, Any] | None = None
        self._finish_reason: str | None = None

    def feed(self, payload: str) -> None:
        payload = payload.strip()
        if not payload or payload == "[DONE]":
            return
        try:
            chunk = json.loads(payload)
        except ValueError:
            return
        if not isinstance(chunk, dict):
            return

        if isinstance(chunk.get("usage"), dict):
            self._usage = chunk["usage"]

        choices = chunk.get("choices") or []
        if not choices:
            return
        choice = choices[0]
        if choice.get("finish_reason") is not None:
            self._finish_reason = choice["finish_reason"]
        delta = choice.get("delta") or {}

        if isinstance(delta.get("content"), str):
            self._content.append(delta["content"])
        if isinstance(delta.get("reasoning_content"), str):
            self._reasoning.append(delta["reasoning_content"])
        for tool_call in delta.get("tool_calls") or []:
            self._merge_tool_call(tool_call)

    def _merge_tool_call(self, tool_call: dict[str, Any]) -> None:
        index = tool_call.get("index", 0)
        entry = self._tool_calls.setdefault(
            index,
            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
        )
        if tool_call.get("id"):
            entry["id"] = tool_call["id"]
        if tool_call.get("type"):
            entry["type"] = tool_call["type"]
        function = tool_call.get("function") or {}
        if function.get("name"):
            entry["function"]["name"] += function["name"]
        if function.get("arguments"):
            entry["function"]["arguments"] += function["arguments"]

    def to_result(self, raw_sse: str) -> StreamResult:
        tool_calls = [self._tool_calls[index] for index in sorted(self._tool_calls)]
        return StreamResult(
            content="".join(self._content),
            reasoning_content="".join(self._reasoning),
            tool_calls=tool_calls,
            usage=self._usage,
            finish_reason=self._finish_reason,
            raw_sse=raw_sse,
        )


def _drain(buffer: bytes, accumulator: SSEAccumulator) -> bytes:
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        _feed_line(line, accumulator)
    return buffer


def _feed_line(line: bytes, accumulator: SSEAccumulator) -> None:
    text = line.decode("utf-8", "replace").strip("\r")
    if text.startswith("data:"):
        accumulator.feed(text[len("data:") :])


OnComplete = Callable[[StreamResult], Awaitable[None]]


async def tee_sse(
    upstream_response: httpx.Response,
    on_complete: OnComplete,
) -> AsyncIterator[bytes]:
    accumulator = SSEAccumulator()
    buffer = b""
    raw_parts: list[bytes] = []
    try:
        async for chunk in upstream_response.aiter_raw():
            raw_parts.append(chunk)
            yield chunk
            buffer = _drain(buffer + chunk, accumulator)
        if buffer:
            _feed_line(buffer, accumulator)
    finally:
        raw_sse = b"".join(raw_parts).decode("utf-8", "replace")
        result = accumulator.to_result(raw_sse)
        await upstream_response.aclose()
        await asyncio.shield(on_complete(result))
