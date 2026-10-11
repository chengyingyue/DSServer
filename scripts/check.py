from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = ROOT / "src" / "dsserver" / "gui"
SVG_NS = "http://www.w3.org/2000/svg"


def run(label: str, args: list[str]) -> bool:
    print(f"\n== {label} ==", flush=True)
    result = subprocess.run(args, cwd=ROOT)
    return result.returncode == 0


def check_gui() -> bool:
    for name in ("app.js", "index.html"):
        text = (GUI_DIR / name).read_text(encoding="utf-8").replace(SVG_NS, "")
        for scheme in ("http://", "https://"):
            if scheme in text:
                print(f"\n== gui ==\n{name} references {scheme}; the GUI must stay offline")
                return False

    node = shutil.which("node")
    if node is None:
        print("\n== gui JS ==\nnode not found on PATH; skipping syntax check")
        return True
    return run("gui JS syntax", [node, "--check", str(GUI_DIR / "app.js")])


def main() -> None:
    checks = [
        run("pytest", [sys.executable, "-m", "pytest", "-q"]),
        run("mypy", [sys.executable, "-m", "mypy"]),
        check_gui(),
    ]
    sys.exit(0 if all(checks) else 1)


if __name__ == "__main__":
    main()
