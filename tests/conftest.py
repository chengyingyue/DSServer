from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from dsserver.app import create_app
from dsserver.config import Config
from dsserver.models import build_chat_response
from dsserver.store import read_records as _read_records
from dsserver.tokens import TokenizerUnavailable

Handler = Callable[[httpx.Request], httpx.Response]


def read_records(config: Config) -> list[dict[str, Any]]:
    return _read_records(config.log_path)


def chat_response(content: str) -> dict[str, Any]:
    return {
        "id": "x",
        "object": "chat.completion",
        "model": "deepseek-flash",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def stored_chat_response(
    content: str = "ok",
    usage: dict[str, Any] | None = None,
    finish_reason: str | None = "stop",
) -> dict[str, Any]:
    return build_chat_response(
        200,
        usage,
        finish_reason,
        {"role": "assistant", "content": content},
    )


def sequence_handler(responses: list[dict[str, Any]]) -> Handler:
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response(200, json.dumps(next(iterator)).encode())

    return handler


def conversation_files(config: Config):
    return sorted(config.conversations_dir.glob("*.md"))


def streaming_response(
    status_code: int = 200,
    content: bytes = b"",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(status_code, stream=httpx.ByteStream(content), headers=headers)


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(
        upstream_base_url="https://upstream.test",
        store_dir=tmp_path / "data",
        bind="127.0.0.1",
        port=8787,
    )


class FakeTokenCounter:
    def count(self, text: str) -> int:
        return len(text.split())


class BrokenTokenCounter:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error if error is not None else TokenizerUnavailable("offline")

    def count(self, text: str) -> int:
        raise self.error


def build_app(
    config: Config,
    handler: Handler,
    token_counter: Any | None = None,
) -> FastAPI:
    counter = FakeTokenCounter() if token_counter is None else token_counter
    return create_app(
        config,
        upstream_transport=httpx.MockTransport(handler),
        token_counter=counter,
    )


def client_for(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://bridge.test",
    )
