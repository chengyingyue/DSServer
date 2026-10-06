from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from dsserver.app import create_app
from dsserver.config import Config
from dsserver.store import read_records as _read_records

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


def build_app(config: Config, handler: Handler) -> FastAPI:
    return create_app(config, upstream_transport=httpx.MockTransport(handler))


def client_for(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://bridge.test",
    )
