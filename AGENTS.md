# DSServer — Agent Guide

## Read first

Orient yourself before starting work:

- Project overview and setup: `README.md`
- Domain vocabulary: `GLOSSARY.md`
- Decision history: `docs/adr/`
- Current feature work (specs + tickets): `.scratch/<feature>/`
- Baseline: run `git status` and `uv run python scripts/check.py` before changing
  code; surface a red baseline before building on it.

## Local server

A background `dsserver` may still be bound to a port with an **older build** —
restart it after code changes with the detached launcher below, and confirm it
serves current code before debugging against it. Confirm readiness with
`Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8788/` or add `--wait` to
the launcher; the log line is not reliable. See `README.md` §Run for the
prod/test port split.

Use `uv run python scripts/restart.py --env test` (port 8788) for testing, and
`--env prod` (port 8787) only when the owner asks. The launcher detaches and
returns immediately. **Do not use `Start-Process` with redirected
stdout/stderr plus `Start-Sleep`** — it has repeatedly hung this environment.
Add `--restart` to replace whatever is already listening on that port.

The test server shares `data/` with production; use it for read-only checks and
keep write tests in pytest temp stores. Stop servers before `uv sync` if
`.venv/Scripts/dsserver.exe` is locked (`--stop --env all`).

Remote Clients (opencode on this PC, the phone) reach the Bridge through
Tailscale. When one of them cannot connect, run
`uv run python scripts/check_remote.py` first: it checks the tailnet state, the
Serve rule and the HTTPS path in one command. See `README.md` §Going remote.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map to identically-named labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
