# 02: Capture a non-streaming Exchange

**What to build:** A successful non-streaming chat request is fully persisted as one line in the append-only JSONL truth log: the complete request messages, the reconstructed assistant message, usage, model, and whitelisted headers. Non-chat requests are recorded as metadata only. The deep-path rule decides which requests get full treatment.

**Blocked by:** 01.

**Status:** done

- [x] A successful non-streaming chat request is recorded as one JSONL line containing the full request messages, reconstructed response message, usage, model, and whitelisted headers.
- [x] The stored record never contains the `Authorization` header; non-whitelisted headers are dropped.
- [x] Deep-path rule applied: `POST` to a configured chat path returning 2xx is fully recorded; every other request is recorded as metadata only (method, path, status, latency).
- [x] Token usage is read from the response when present and stored; otherwise left empty.
- [x] Records carry `owner` (default `local`) and a `kind` distinguishing chat from other.
- [x] Persistence is serialized so concurrent writes never corrupt the log.

## Comments

- Verified done: `tests/test_capture_non_streaming.py`, `tests/test_passthrough.py`, and `tests/test_console_tokens.py`.
