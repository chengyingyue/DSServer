from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except ValueError:
            continue
    return records


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: list[dict[str, Any]] = read_records(path)
        self._lock = asyncio.Lock()

    async def append(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False)
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
            self.records.append(record)

    async def purge(self, ids: set[str]) -> int:
        async with self._lock:
            remaining = [record for record in self.records if record.get("id") not in ids]
            removed = len(self.records) - len(remaining)
            if not removed:
                return 0
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, tmp_name = tempfile.mkstemp(
                suffix=".jsonl", dir=self.path.parent
            )
            os.close(handle)
            tmp = Path(tmp_name)
            try:
                with tmp.open("w", encoding="utf-8") as writer:
                    for record in remaining:
                        writer.write(json.dumps(record, ensure_ascii=False) + "\n")
                os.replace(tmp, self.path)
            except Exception:
                tmp.unlink(missing_ok=True)
                raise
            self.records = remaining
            return removed
