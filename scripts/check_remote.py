from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request

EXPECTED_TARGET = "http://127.0.0.1:8787"
PATHS = ("/", "/api/conversations")


def run(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def tailscale_status() -> dict[str, object] | None:
    result = run(["tailscale", "status", "--json"])
    if result is None or result.returncode != 0:
        return None
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return status if isinstance(status, dict) else None


def check_backend(status: dict[str, object]) -> tuple[bool, str]:
    state = status.get("BackendState", "?")
    health = "; ".join(str(item) for item in status.get("Health") or [])
    if state == "Running":
        return True, "BackendState=Running"
    detail = f"BackendState={state}"
    return False, f"{detail} ({health})" if health else detail


def check_serve() -> tuple[bool, str]:
    result = run(["tailscale", "serve", "status"])
    if result is None or result.returncode != 0:
        return False, "tailscale serve status failed"
    text = result.stdout
    if "https://" in text and EXPECTED_TARGET in text:
        return True, f"443 -> {EXPECTED_TARGET}"
    return False, f"no Serve rule for https -> {EXPECTED_TARGET}"


def check_http(url: str) -> tuple[bool, str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=10) as response:
            ok = response.status == 200
            return ok, f"{url} -> {response.status}"
    except (urllib.error.URLError, OSError) as exc:
        return False, f"{url} -> {exc}"


def main() -> None:
    status = tailscale_status()
    if status is None:
        print("FAIL tailscale: CLI not found or status is unavailable")
        raise SystemExit(1)

    checks: list[tuple[str, bool, str]] = []
    ok, detail = check_backend(status)
    checks.append(("tailscale", ok, detail))

    self_info = status.get("Self")
    dns_name = ""
    if isinstance(self_info, dict):
        dns_name = str(self_info.get("DNSName") or "").rstrip(".")
    if not dns_name:
        checks.append(("dns name", False, "Self.DNSName is empty; is MagicDNS on?"))
    else:
        checks.append(("dns name", True, dns_name))

    ok, detail = check_serve()
    checks.append(("serve", ok, detail))

    if dns_name:
        for path in PATHS:
            ok, detail = check_http(f"https://{dns_name}{path}")
            checks.append((f"https {path}", ok, detail))

    for label, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")

    raise SystemExit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
