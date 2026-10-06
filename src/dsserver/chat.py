from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

KNOWN_REQUEST_KEYS = {"messages", "model", "stream", "tools"}


@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    model: str | None
    stream: bool
    tools: Any
    params: dict[str, Any]

    def to_request_dict(self, path: str) -> dict[str, Any]:
        return {
            "method": "POST",
            "path": path,
            "model": self.model,
            "stream": self.stream,
            "messages": self.messages,
            "tools": self.tools,
            "params": self.params,
        }


def parse_chat_request(body: bytes) -> ChatRequest:
    data = json.loads(body)
    if not isinstance(data, dict) or "messages" not in data:
        raise ValueError("not a chat request")
    return ChatRequest(
        messages=list(data.get("messages", [])),
        model=data.get("model"),
        stream=bool(data.get("stream", False)),
        tools=data.get("tools"),
        params={key: value for key, value in data.items() if key not in KNOWN_REQUEST_KEYS},
    )


def parse_chat_response(body: bytes) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("not a chat response")
    choices = data.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    return message, data.get("usage"), choice.get("finish_reason")
