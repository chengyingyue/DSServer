from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from tokenizers import Tokenizer

from .config import TOKENIZER_LABEL
from .markdown import smart_zone_percent

TOKENIZER_URL = "https://cdn.deepseek.com/api-docs/deepseek_v4_tokenizer.zip"
TOKENIZER_SHA256 = "89085F12EF79460AC5F66D1119325DDFC694B4AB209D80BBD81D35F081DC9614"
TOKENIZER_MEMBER = "deepseek_v4_tokenizer/tokenizer.json"
TOKENIZER_FILENAME = "tokenizer.json"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
JSON_SUFFIXES = {".json", ".jsonl"}
KNOWN_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".jsonl"}

_DOWNLOAD_LOCK = threading.Lock()


class TokenError(Exception):
    pass


class TokenizerUnavailable(TokenError):
    pass


class TokenInputError(TokenError, ValueError):
    pass


class Counter(Protocol):
    def count(self, text: str) -> int: ...


class TokenCounter:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._tokenizer: Tokenizer | None = None
        self._lock = threading.Lock()

    @property
    def cache_path(self) -> Path:
        return self._cache_dir / TOKENIZER_FILENAME

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._load().encode(text, add_special_tokens=False).ids)

    def _load(self) -> Tokenizer:
        if self._tokenizer is None:
            with self._lock:
                if self._tokenizer is None:
                    self._tokenizer = load_tokenizer(self._cache_dir)
        return self._tokenizer


@dataclass(frozen=True)
class TokenEstimate:
    filename: str
    tokens: int
    characters: int
    lines: int
    size_bytes: int
    mode: str
    encoding: str
    smart_zone_tokens: int
    smart_zone_percent: int | None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "tokens": self.tokens,
            "characters": self.characters,
            "lines": self.lines,
            "bytes": self.size_bytes,
            "mode": self.mode,
            "encoding": self.encoding,
            "tokenizer": TOKENIZER_LABEL,
            "smart_zone_tokens": self.smart_zone_tokens,
            "smart_zone_percent": self.smart_zone_percent,
            "warning": self.warning,
        }


def load_tokenizer(cache_dir: Path) -> Tokenizer:
    path = _ensure_tokenizer(cache_dir)
    try:
        return Tokenizer.from_file(str(path))
    except Exception as error:
        raise TokenizerUnavailable(f"cannot load {path}: {error}") from error


def _ensure_tokenizer(cache_dir: Path) -> Path:
    path = cache_dir / TOKENIZER_FILENAME
    with _DOWNLOAD_LOCK:
        if path.exists():
            cached = path.read_bytes()
            if _digest(cached) == TOKENIZER_SHA256:
                return path
        data = _download_tokenizer()
        cache_dir.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(prefix="tokenizer-", suffix=".json", dir=cache_dir)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    return path


def _download_tokenizer() -> bytes:
    try:
        with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            response = client.get(TOKENIZER_URL)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise TokenizerUnavailable(f"cannot download tokenizer: {error}") from error
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            data = archive.read(TOKENIZER_MEMBER)
    except (zipfile.BadZipFile, KeyError) as error:
        raise TokenizerUnavailable(f"invalid tokenizer archive: {error}") from error
    if _digest(data) != TOKENIZER_SHA256:
        raise TokenizerUnavailable(
            "tokenizer checksum mismatch; update TOKENIZER_SHA256 in dsserver.tokens"
        )
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def decode_text(data: bytes, encoding: str = "utf-8") -> str:
    normalized = encoding.lower().replace("_", "-")
    if normalized in {"utf-8", "utf8"}:
        normalized = "utf-8-sig"
    try:
        return data.decode(normalized)
    except LookupError as error:
        raise TokenInputError(f"unknown encoding: {encoding}") from error
    except UnicodeDecodeError as error:
        raise TokenInputError(f"cannot decode as {encoding}: {error}") from error


def message_content(message: Any) -> str | None:
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    parts: list[str] = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            parts.append(text)
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if not parts:
        return None
    return "\n".join(parts)


def messages_text(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        text = message_content(message)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _response_text(response: Any) -> list[str]:
    if not isinstance(response, dict):
        return []
    parts: list[str] = []
    text = message_content(response.get("message"))
    if text:
        parts.append(text)
    choices = response.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if isinstance(choice, dict):
                text = message_content(choice.get("message"))
                if text:
                    parts.append(text)
    return parts


def _collect_chat(value: Any, include_response: bool) -> list[str]:
    if isinstance(value, list):
        if value and all(isinstance(item, dict) and "role" in item for item in value):
            joined = messages_text(value)
            return [joined] if joined else []
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_chat(item, include_response))
        return collected
    if not isinstance(value, dict):
        return []
    collected = []
    messages = value.get("messages")
    if isinstance(messages, list):
        joined = messages_text(messages)
        if joined:
            collected.append(joined)
    request = value.get("request")
    if isinstance(request, dict):
        request_messages = request.get("messages")
        if isinstance(request_messages, list):
            request_text = messages_text(request_messages)
            if request_text:
                collected.append(request_text)
    if include_response:
        response = value.get("response")
        if isinstance(response, dict):
            collected.extend(_response_text(response))
        elif "choices" in value:
            collected.extend(_response_text(value))
    return collected


def extract_json_text(value: Any, *, include_response: bool = True) -> str | None:
    parts = _collect_chat(value, include_response)
    if not parts:
        return None
    return "\n".join(parts)


def extract_jsonl_text(text: str, *, include_response: bool = True) -> str | None:
    parts: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise TokenInputError(f"invalid JSON on line {number}: {error.msg}") from error
        parts.extend(_collect_chat(value, include_response))
    if not parts:
        return None
    return "\n".join(parts)


def estimate_upload(
    data: bytes,
    filename: str,
    *,
    encoding: str,
    raw: bool,
    counter: Counter,
    smart_zone: int,
) -> TokenEstimate:
    text = decode_text(data, encoding)
    counted = text
    mode = "raw"
    suffix = Path(filename).suffix.lower()
    warning = None
    if suffix not in KNOWN_SUFFIXES:
        warning = f"unknown extension {suffix or '(none)'}; counted as raw text"
    if not raw and suffix in JSON_SUFFIXES and text.strip():
        if suffix == ".json":
            try:
                value = json.loads(text)
            except json.JSONDecodeError as error:
                raise TokenInputError(f"invalid JSON: {error.msg} (line {error.lineno})") from error
            extracted = extract_json_text(value)
        else:
            extracted = extract_jsonl_text(text)
        if extracted is not None:
            counted = extracted
            mode = "chat"
    tokens = counter.count(counted)
    return TokenEstimate(
        filename=filename,
        tokens=tokens,
        characters=len(text),
        lines=len(text.splitlines()),
        size_bytes=len(data),
        mode=mode,
        encoding=encoding,
        smart_zone_tokens=smart_zone,
        smart_zone_percent=smart_zone_percent(tokens, smart_zone),
        warning=warning,
    )


def count_messages(messages: list[dict[str, Any]], counter: Counter) -> int:
    return counter.count(messages_text(messages))
