from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def unique_name(name: str, exists: Callable[[str], bool]) -> str:
    if not exists(name):
        return name
    suffix = Path(name).suffix
    stem = name[: -len(suffix)] if suffix else name
    counter = 2
    while exists(f"{stem}-{counter}{suffix}"):
        counter += 1
    return f"{stem}-{counter}{suffix}"
