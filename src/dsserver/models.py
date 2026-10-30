from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

CHAT_KIND = "chat"
SAVE_KIND = "save"
OTHER_KIND = "other"
RENAME_KIND = "rename"
FOLDER_KIND = "folder"
RENDER_NORMAL = "normal"
RENDER_PLAIN_CODE = "plain_code"
RENDER_MODES = (RENDER_NORMAL, RENDER_PLAIN_CODE)


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ClientInfo:
    user_agent: str
    headers: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {"user_agent": self.user_agent, "headers": self.headers}


def build_client_info(headers: Mapping[str, str], whitelist: Sequence[str]) -> ClientInfo:
    allowed = {name.lower() for name in whitelist}
    captured: dict[str, str] = {}
    user_agent = ""
    for name, value in headers.items():
        lowered = name.lower()
        if lowered == "authorization" or lowered not in allowed:
            continue
        captured[lowered] = value
        if lowered == "user-agent":
            user_agent = value
    return ClientInfo(user_agent=user_agent, headers=captured)


def build_chat_response(
    status: int,
    usage: dict[str, Any] | None,
    finish_reason: str | None,
    message: dict[str, Any],
) -> dict[str, Any]:
    return {"status": status, "usage": usage, "finish_reason": finish_reason, "message": message}


@dataclass
class Exchange:
    id: str
    owner: str
    ts: str
    kind: str
    client: ClientInfo
    request: dict[str, Any]
    response: dict[str, Any]
    meta: dict[str, Any]
    raw_sse: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "owner": self.owner,
            "ts": self.ts,
            "kind": self.kind,
            "client": self.client.to_dict(),
            "request": self.request,
            "response": self.response,
            "meta": self.meta,
        }
        if self.raw_sse is not None:
            data["raw_sse"] = self.raw_sse
        return data


def build_exchange(
    kind: str,
    client: ClientInfo,
    request: dict[str, Any],
    response: dict[str, Any],
    meta: dict[str, Any],
    raw_sse: str | None = None,
    owner: str = "local",
    ts: str | None = None,
) -> Exchange:
    return Exchange(
        id=new_id(),
        owner=owner,
        ts=ts or now_iso(),
        kind=kind,
        client=client,
        request=request,
        response=response,
        meta=meta,
        raw_sse=raw_sse,
    )


def build_rename(key: str, branch: int, name: str, owner: str = "local") -> dict[str, Any]:
    return {
        "id": new_id(),
        "owner": owner,
        "ts": now_iso(),
        "kind": RENAME_KIND,
        "key": key,
        "branch": branch,
        "name": name,
    }


def build_folder(
    op: str, folder: str, owner: str = "local", **fields: Any
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": new_id(),
        "owner": owner,
        "ts": now_iso(),
        "kind": FOLDER_KIND,
        "op": op,
        "folder": folder,
    }
    record.update(fields)
    return record
