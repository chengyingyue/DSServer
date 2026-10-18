from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


def port_for(env: str) -> int:
    path = ROOT / "config.toml"
    if not path.exists():
        return 8788 if env == "test" else 8787
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    default = 8788 if env == "test" else 8787
    return int(data.get("test_port" if env == "test" else "port", default))


def command(env: str) -> list[str]:
    executable = Path(sys.executable).with_name("dsserver.exe" if os.name == "nt" else "dsserver")
    if executable.exists():
        return [str(executable), "serve", "--env", env]
    return [sys.executable, "-m", "dsserver", "serve", "--env", env]


def find_pid_on_port(port: int) -> int | None:
    try:
        if os.name == "nt":
            output = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
            ).stdout
            for line in output.splitlines():
                fields = line.split()
                if (
                    len(fields) >= 5
                    and fields[0].upper() == "TCP"
                    and fields[1].endswith(f":{port}")
                    and fields[3].upper() == "LISTENING"
                ):
                    try:
                        return int(fields[4])
                    except ValueError:
                        continue
            return None
        output = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        ).stdout
        for line in output.splitlines():
            try:
                return int(line.strip())
            except ValueError:
                continue
    except OSError:
        return None
    return None


def stop_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        os.kill(pid, signal.SIGTERM)


def wait_for_port(port: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if find_pid_on_port(port) is None:
            return True
        time.sleep(0.2)
    return find_pid_on_port(port) is None


def wait_for_http(port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


def stop(env: str) -> None:
    for name in ("prod", "test") if env == "all" else (env,):
        port = port_for(name)
        pid = find_pid_on_port(port)
        if pid is None:
            print(f"no dsserver listening on port {port} ({name})")
            continue
        stop_pid(pid)
        if wait_for_port(port):
            print(f"stopped dsserver ({name}) on port {port}, pid {pid}")
        else:
            print(f"port {port} is still in use after stopping pid {pid}")


def start(env: str, port: int) -> None:
    log_path = ROOT / f"dsserver-{env}.log"
    error_path = ROOT / f"dsserver-{env}.err.log"
    with log_path.open("ab") as output, error_path.open("ab") as error:
        if os.name == "nt":
            process = subprocess.Popen(
                command(env),
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=error,
                close_fds=True,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            )
        else:
            process = subprocess.Popen(
                command(env),
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=error,
                close_fds=True,
                start_new_session=True,
            )
    print(f"started dsserver ({env}) on port {port}, pid {process.pid}")
    print(f"logs: {log_path.name}, {error_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start or restart a detached dsserver.")
    parser.add_argument("--env", choices=["prod", "test", "all"], default="test")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    if args.stop:
        stop(args.env)
        return
    if args.env == "all":
        parser.error("--env all is only valid with --stop")

    port = port_for(args.env)
    pid = find_pid_on_port(port)
    if pid is not None:
        if not args.restart:
            print(f"port {port} is already in use by pid {pid}; rerun with --restart")
            raise SystemExit(1)
        stop_pid(pid)
        if not wait_for_port(port):
            print(f"port {port} is still in use after stopping pid {pid}")
            raise SystemExit(1)
    start(args.env, port)
    if args.wait:
        if wait_for_http(port):
            print(f"ready: http://127.0.0.1:{port}/")
        else:
            print(f"not ready after 10s: http://127.0.0.1:{port}/")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
