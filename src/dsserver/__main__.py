from __future__ import annotations

import argparse
import socket
import sys

import uvicorn

from .app import create_app
from .config import load_config
from .markdown import render_all


def refuse_busy_port(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            print(
                f"Port {port} on {host} is already in use — another dsserver is probably"
                f" still running.\nStop it and retry, e.g.:  Stop-Process -Name dsserver -Force",
                file=sys.stderr,
            )
            raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="dsserver")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "render"])
    parser.add_argument("--config", default="config.toml")
    parser.add_argument(
        "--env",
        default="prod",
        choices=["prod", "test"],
        help="which port to serve on: prod (port) or test (test_port)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if args.command == "render":
        count = render_all(config)
        print(f"Rendered {count} conversation(s) into {config.conversations_dir}")
        return

    port = config.port_for(args.env)
    refuse_busy_port(config.bind, port)
    print(f"Serving on {config.bind}:{port} ({args.env})")
    uvicorn.run(create_app(config), host=config.bind, port=port, workers=1)


if __name__ == "__main__":
    main()
