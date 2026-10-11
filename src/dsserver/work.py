from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_HEADING_RE = re.compile(r"^#\s+(.*)$")


class WorkCopyError(Exception):
    """Raised when a work copy cannot be found or addressed."""


def default_name(content: str) -> str:
    for line in content.splitlines():
        heading = _HEADING_RE.match(line.strip())
        if heading is not None and heading.group(1).strip():
            return heading.group(1).strip()
    return "Work Copy"


class WorkStore:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self._names_path = self.directory / ".names.json"

    def _path(self, work_id: str) -> Path:
        if not _ID_RE.match(work_id):
            raise WorkCopyError(f"unknown work copy: {work_id}")
        return self.directory / f"{work_id}.md"

    def _load_names(self) -> dict[str, str]:
        if not self._names_path.is_file():
            return {}
        try:
            data = json.loads(self._names_path.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _save_names(self, names: dict[str, str]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self._names_path.write_text(
            json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create(self, content: str, name: str | None = None) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        work_id = uuid.uuid4().hex
        self._path(work_id).write_text(content, encoding="utf-8")
        chosen = name.strip() if isinstance(name, str) and name.strip() else default_name(content)
        names = self._load_names()
        names[work_id] = chosen
        self._save_names(names)
        return work_id

    def read(self, work_id: str) -> str:
        path = self._path(work_id)
        if not path.is_file():
            raise WorkCopyError(f"unknown work copy: {work_id}")
        return path.read_text(encoding="utf-8")

    def save(self, work_id: str, content: str) -> None:
        path = self._path(work_id)
        if not path.is_file():
            raise WorkCopyError(f"unknown work copy: {work_id}")
        path.write_text(content, encoding="utf-8")

    def discard(self, work_id: str) -> None:
        path = self._path(work_id)
        if not path.is_file():
            raise WorkCopyError(f"unknown work copy: {work_id}")
        path.unlink()
        names = self._load_names()
        if names.pop(work_id, None) is not None:
            self._save_names(names)

    def name(self, work_id: str) -> str:
        content_path = self._path(work_id)
        names = self._load_names()
        if work_id in names:
            return names[work_id]
        if not content_path.is_file():
            raise WorkCopyError(f"unknown work copy: {work_id}")
        return default_name(content_path.read_text(encoding="utf-8"))

    def rename(self, work_id: str, name: str) -> str:
        if not self._path(work_id).is_file():
            raise WorkCopyError(f"unknown work copy: {work_id}")
        chosen = name.strip()
        if not chosen:
            raise WorkCopyError("name is required")
        names = self._load_names()
        names[work_id] = chosen
        self._save_names(names)
        return chosen

    def list(self) -> list[dict[str, str]]:
        if not self.directory.is_dir():
            return []
        entries: list[dict[str, str]] = []
        for path in sorted(self.directory.glob("*.md")):
            work_id = path.stem
            if not _ID_RE.match(work_id):
                continue
            entries.append({"id": work_id, "name": self.name(work_id)})
        return entries
