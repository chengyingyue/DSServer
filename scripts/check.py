from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(label: str, args: list[str]) -> bool:
    print(f"\n== {label} ==", flush=True)
    result = subprocess.run(args, cwd=ROOT)
    return result.returncode == 0


def check_gui_js() -> bool:
    from dsserver.gui import INDEX_HTML

    match = re.search(r"<script>(.*)</script>", INDEX_HTML, re.S)
    if match is None:
        print("\n== gui JS ==\nno <script> block found in gui.py")
        return False
    js = match.group(1)

    network_js = js.replace("http://www.w3.org/2000/svg", "")
    for scheme in ("http://", "https://"):
        if scheme in network_js:
            print(f"\n== gui JS ==\nembedded JS references {scheme}; the GUI must stay offline")
            return False

    node = shutil.which("node")
    if node is None:
        print("\n== gui JS ==\nnode not found on PATH; skipping syntax check")
        return True

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(js)
        path = handle.name
    try:
        return run("gui JS syntax", [node, "--check", path])
    finally:
        Path(path).unlink(missing_ok=True)


def main() -> None:
    checks = [
        run("pytest", [sys.executable, "-m", "pytest", "-q"]),
        run("mypy", [sys.executable, "-m", "mypy"]),
        check_gui_js(),
    ]
    sys.exit(0 if all(checks) else 1)


if __name__ == "__main__":
    main()
