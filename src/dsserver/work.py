from __future__ import annotations

import re
import uuid
from pathlib import Path

_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class WorkCopyError(Exception):
    """Raised when a work copy cannot be found or addressed."""


class WorkStore:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, work_id: str) -> Path:
        if not _ID_RE.match(work_id):
            raise WorkCopyError(f"unknown work copy: {work_id}")
        return self.directory / f"{work_id}.md"

    def create(self, content: str) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        work_id = uuid.uuid4().hex
        self._path(work_id).write_text(content, encoding="utf-8")
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
