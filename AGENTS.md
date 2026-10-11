# DSServer — Agent Guide

## Read first

Orient yourself before starting work:

- Project overview and setup: `README.md`
- Domain vocabulary: `GLOSSARY.md`
- Decision history: `docs/adr/`
- Current feature work (specs + tickets): `.scratch/<feature>/`

## Local server

A background `dsserver` may still be bound to a port with an **older build** —
restart it after code changes, and confirm it serves current code before
debugging against it. It is up when stderr shows `Uvicorn running on ...`
(stdout may stay empty under redirection). See `README.md` §Run for the
prod/test port split.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map to identically-named labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
