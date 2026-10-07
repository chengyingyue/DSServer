from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

CHAT_KIND = "chat"
OTHER_KIND = "other"
RENAME_KIND = "rename"


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
) -> Exchange:
    return Exchange(
        id=new_id(),
        owner=owner,
        ts=now_iso(),
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
