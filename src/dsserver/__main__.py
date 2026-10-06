from __future__ import annotations

import argparse

import uvicorn

from .app import create_app
from .config import load_config
from .markdown import render_all


def main() -> None:
    parser = argparse.ArgumentParser(prog="dsserver")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "render"])
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.command == "render":
        count = render_all(config)
        print(f"Rendered {count} conversation(s) into {config.conversations_dir}")
        return

    uvicorn.run(create_app(config), host=config.bind, port=config.port, workers=1)


if __name__ == "__main__":
    main()
