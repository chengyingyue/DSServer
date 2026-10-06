from __future__ import annotations

import asyncio
import json
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
