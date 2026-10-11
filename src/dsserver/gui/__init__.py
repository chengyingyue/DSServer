from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent


def _assemble() -> str:
    template = (_DIR / "index.html").read_text(encoding="utf-8")
    styles = (_DIR / "app.css").read_text(encoding="utf-8")
    script = (_DIR / "app.js").read_text(encoding="utf-8")
    return template.replace("%%STYLES%%", styles).replace("%%SCRIPT%%", script)


INDEX_HTML = _assemble()
