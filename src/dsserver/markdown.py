from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config
from .models import FOLDER_KIND, RENAME_KIND, RENDER_NORMAL
from .naming import unique_name
from .store import read_records

SECTION_LABELS = {
    "system": "Injected (system)",
    "user": "Human (user)",
    "assistant": "Assistant",
    "tool": "Tool",
}


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _signature(message: dict[str, Any]) -> tuple[str, str]:
    return (str(message.get("role", "")), _content_text(message.get("content")))


def _first_message_with_role(msgs: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    for message in msgs:
        if message.get("role") == role:
            return message
    return None


def conversation_key(msgs: list[dict[str, Any]]) -> str:
    system = _first_message_with_role(msgs, "system")
    user = _first_message_with_role(msgs, "user")
    basis = json.dumps(
        {
            "system": _signature(system) if system else None,
            "user": _signature(user) if user else None,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def _slug(msgs: list[dict[str, Any]]) -> str:
    user = _first_message_with_role(msgs, "user")
    text = _content_text(user.get("content")) if user else ""
    slug = re.sub(r"[^\w]+", "-", text.lower()).strip("-_")
    return slug[:40].strip("-_")


def _title(msgs: list[dict[str, Any]]) -> str:
    user = _first_message_with_role(msgs, "user")
    text = _content_text(user.get("content")).strip() if user else ""
    if not text:
        return "Conversation"
    first_line = text.splitlines()[0]
    return first_line[:60]


_WINDOWS_RESERVED_STEMS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}


def sanitize_stem(name: str) -> str:
    text = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "-", name)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(". ")
    if text.upper() in _WINDOWS_RESERVED_STEMS:
        text = f"name{text}"
    return text[:80].strip(". ") or "conversation"


def _unique_filename(stem: str, used_names: set[str]) -> str:
    candidate = unique_name(f"{stem}.md", lambda name: name.lower() in used_names)
    used_names.add(candidate.lower())
    return candidate


@dataclass
class Turn:
    new_messages: list[dict[str, Any]]
    response_message: dict[str, Any]
    ts: str
    model: str | None
    usage: dict[str, Any] | None
    latency_ms: int | None
    finish_reason: str | None


@dataclass
class Conversation:
    key: str
    filename: str
    title: str
    date: str
    model: str | None
    branch: int = 0
    name: str | None = None
    name_ts: str = ""
    name_order: int = 0
    history: list[tuple[str, str]] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    record_ids: list[str] = field(default_factory=list)


def _new_conversation(
    key: str,
    msgs: list[dict[str, Any]],
    record: dict[str, Any],
    used_names: set[str],
    branch: int,
) -> Conversation:
    date = str(record.get("ts", ""))[:10]
    slug = _slug(msgs) or key[:8]
    stem = f"{date}-{slug}"
    if branch > 0:
        stem = f"{stem}-b{branch + 1}"
    return Conversation(
        key=key,
        filename=_unique_filename(stem, used_names),
        title=_title(msgs),
        date=date,
        model=(record.get("request") or {}).get("model"),
        branch=branch,
    )


class ConversationIndex:
    def __init__(self) -> None:
        self._states: dict[str, list[Conversation]] = {}
        self._order: list[Conversation] = []
        self._used_names: set[str] = set()
        self._seq = 0
        self._folders: dict[str, dict[str, Any]] = {}
        self._folder_order: list[str] = []
        self._assignments: dict[tuple[str, int], tuple[str, int]] = {}
        self._renders: dict[str, tuple[str, int]] = {}

    @property
    def conversations(self) -> list[Conversation]:
        return list(self._order)

    def get(self, key: str, branch: int = 0) -> Conversation | None:
        branches = self._states.get(key)
        if branches is None or branch < 0 or branch >= len(branches):
            return None
        return branches[branch]

    def has_folder(self, folder: str) -> bool:
        if not folder:
            return True
        entry = self._folders.get(folder)
        return entry is not None and not entry.get("deleted")

    def folders(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for folder_id in self._folder_order:
            entry = self._folders.get(folder_id)
            if entry is None or entry.get("deleted"):
                continue
            result.append(
                {
                    "id": folder_id,
                    "name": entry["name"],
                    "parent": self._live_parent(entry.get("parent") or ""),
                    "render": self._render_for_folder(folder_id),
                }
            )
        return result

    def folder_of(self, conversation: Conversation) -> str:
        assignment = self._assignments.get((conversation.key, conversation.branch))
        if assignment is None:
            return ""
        return self._live_parent(assignment[0])

    def render_mode_of(self, conversation: Conversation) -> str:
        return self._render_for_folder(self.folder_of(conversation))

    def _render_for_folder(self, folder: str) -> str:
        seen: set[str] = set()
        while folder and folder not in seen:
            seen.add(folder)
            mode = self._renders.get(folder)
            if mode is not None:
                return mode[0]
            entry = self._folders.get(folder)
            if entry is None:
                break
            folder = self._live_parent(entry.get("parent") or "")
        return RENDER_NORMAL

    def _live_parent(self, parent: str) -> str:
        seen: set[str] = set()
        current = parent
        while current and current not in seen:
            seen.add(current)
            entry = self._folders.get(current)
            if entry is None:
                return ""
            if not entry.get("deleted"):
                return current
            current = entry.get("parent") or ""
        return ""

    def name_in_use(self, name: str, conversation: Conversation) -> bool:
        candidate = f"{sanitize_stem(name)}.md".lower()
        return any(
            other is not conversation and other.filename.lower() == candidate
            for other in self._order
        )

    @classmethod
    def from_records(cls, records: list[dict[str, Any]]) -> "ConversationIndex":
        index = cls()
        for record in records:
            index.apply(record)
        return index

    def apply(self, record: dict[str, Any]) -> Conversation | None:
        self._seq += 1
        kind = record.get("kind")
        if kind == RENAME_KIND:
            return self._apply_rename(record, self._seq)
        if kind == FOLDER_KIND:
            self._apply_folder(record, self._seq)
            return None
        if kind != "chat":
            return None
        request = record.get("request") or {}
        msgs = request.get("messages") or []
        if not msgs:
            return None
        signatures = [_signature(message) for message in msgs]
        key = conversation_key(msgs)
        response_message = (record.get("response") or {}).get("message") or {}

        branches = self._states.setdefault(key, [])
        conversation: Conversation | None = None
        new_messages: list[dict[str, Any]] = msgs
        for candidate in reversed(branches):
            history = candidate.history
            if len(signatures) >= len(history) and signatures[: len(history)] == history:
                conversation = candidate
                new_messages = msgs[len(history) :]
                break

        if conversation is None:
            conversation = _new_conversation(key, msgs, record, self._used_names, len(branches))
            branches.append(conversation)
            self._order.append(conversation)
            new_messages = msgs

        conversation.turns.append(
            Turn(
                new_messages=new_messages,
                response_message=response_message,
                ts=str(record.get("ts", "")),
                model=request.get("model"),
                usage=(record.get("response") or {}).get("usage"),
                latency_ms=(record.get("meta") or {}).get("latency_ms"),
                finish_reason=(record.get("response") or {}).get("finish_reason"),
            )
        )
        conversation.history = signatures + [_signature(response_message)]
        record_id = record.get("id")
        if isinstance(record_id, str):
            conversation.record_ids.append(record_id)
        return conversation

    def _apply_rename(self, record: dict[str, Any], order: int) -> Conversation | None:
        key = record.get("key")
        if not isinstance(key, str):
            return None
        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        try:
            branch = int(record.get("branch", 0) or 0)
        except (TypeError, ValueError):
            return None
        conversation = self.get(key, branch)
        if conversation is None:
            return None
        ts = str(record.get("ts", ""))
        if conversation.name is not None and (ts, order) < (
            conversation.name_ts,
            conversation.name_order,
        ):
            return conversation
        self._used_names.discard(conversation.filename.lower())
        conversation.filename = _unique_filename(sanitize_stem(name), self._used_names)
        conversation.name = name.strip()
        conversation.name_ts = ts
        conversation.name_order = order
        record_id = record.get("id")
        if isinstance(record_id, str):
            conversation.record_ids.append(record_id)
        return conversation

    def _apply_folder(self, record: dict[str, Any], order: int) -> None:
        op = record.get("op")
        folder = record.get("folder")
        if not isinstance(folder, str):
            return
        if op == "create":
            name = record.get("name")
            if not isinstance(name, str) or not name.strip() or folder in self._folders:
                return
            parent = record.get("parent")
            self._folders[folder] = {
                "id": folder,
                "name": name.strip(),
                "parent": parent if isinstance(parent, str) else "",
                "deleted": False,
            }
            self._folder_order.append(folder)
            return
        if op == "assign":
            key = record.get("key")
            if not isinstance(key, str):
                return
            try:
                branch = int(record.get("branch", 0) or 0)
            except (TypeError, ValueError):
                return
            conversation = self.get(key, branch)
            if conversation is None:
                return
            previous = self._assignments.get((key, branch))
            if previous is not None and previous[1] > order:
                return
            self._assignments[(key, branch)] = (folder, order)
            record_id = record.get("id")
            if isinstance(record_id, str):
                conversation.record_ids.append(record_id)
            return
        entry = self._folders.get(folder)
        if entry is None:
            return
        if op == "rename":
            name = record.get("name")
            if isinstance(name, str) and name.strip():
                entry["name"] = name.strip()
            return
        if op == "delete":
            entry["deleted"] = True
            return
        if op == "render":
            mode = record.get("mode")
            if not isinstance(mode, str):
                return
            previous = self._renders.get(folder)
            if previous is not None and previous[1] > order:
                return
            self._renders[folder] = (mode, order)
            return


def build_conversations(records: list[dict[str, Any]]) -> list[Conversation]:
    return ConversationIndex.from_records(records).conversations


def render_conversation(conversation: Conversation) -> str:
    models = [model for model in dict.fromkeys(turn.model for turn in conversation.turns) if model]
    summary = f"_{conversation.date} · {len(conversation.turns)} turns"
    if models:
        summary += f" · {', '.join(models)}"
    summary += "_"

    lines: list[str] = [f"# {conversation.title}", "", summary, ""]

    for index, turn in enumerate(conversation.turns, 1):
        header = f"## Turn {index} · {turn.ts}"
        if turn.model:
            header += f" · {turn.model}"
        usage = turn.usage or {}
        if usage.get("total_tokens") is not None:
            header += f" · {usage['total_tokens']} tokens"
        if turn.latency_ms is not None:
            header += f" · {turn.latency_ms} ms"
        lines.extend([header, ""])

        for message in turn.new_messages:
            role = str(message.get("role", ""))
            label = SECTION_LABELS.get(role, role or "Message")
            lines.extend([f"### {label}", ""])
            text = _content_text(message.get("content"))
            if text:
                lines.extend(["```", text, "```"])
            lines.append("")

        response = turn.response_message
        lines.extend(["### Assistant", ""])
        reasoning = _content_text(response.get("reasoning_content"))
        if reasoning:
            lines.append("> reasoning:")
            lines.extend(f"> {line}" for line in reasoning.splitlines())
            lines.append("")
        content = _content_text(response.get("content"))
        if content:
            lines.extend(["```", content, "```"])
        if response.get("tool_calls"):
            lines.extend(["", "tool_calls:", "```json"])
            lines.append(json.dumps(response["tool_calls"], ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")

    return "\n".join(lines)


def render_index(conversations: list[Conversation]) -> str:
    lines = ["# Conversations", "", "| Date | Title | Turns |", "| --- | --- | --- |"]
    for conversation in sorted(conversations, key=lambda c: (c.date, c.filename), reverse=True):
        lines.append(
            f"| {conversation.date} | [{conversation.title}](conversations/{conversation.filename}) "
            f"| {len(conversation.turns)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def write_conversation(config: Config, conversation: Conversation) -> None:
    config.conversations_dir.mkdir(parents=True, exist_ok=True)
    target = config.conversations_dir / conversation.filename
    _write_if_changed(target, render_conversation(conversation))


def write_index(config: Config, conversations: list[Conversation]) -> None:
    _write_if_changed(config.index_path, render_index(conversations))


def write_conversations_dir(config: Config, conversations: list[Conversation]) -> set[str]:
    config.conversations_dir.mkdir(parents=True, exist_ok=True)
    written: set[str] = set()
    for conversation in conversations:
        write_conversation(config, conversation)
        written.add(conversation.filename)
    for existing in config.conversations_dir.glob("*.md"):
        if existing.name not in written:
            existing.unlink()
    return written


def _write(config: Config, conversations: list[Conversation]) -> int:
    write_conversations_dir(config, conversations)
    write_index(config, conversations)
    return len(conversations)


def write_markdown(config: Config, records: list[dict[str, Any]]) -> int:
    return _write(config, build_conversations(records))


def render_all(config: Config) -> int:
    return write_markdown(config, read_records(config.log_path))
