# 01: Bridge skeleton + byte-faithful passthrough

**What to build:** A runnable Bridge that loads `config.toml` and forwards any request from a Client to the Upstream, returning the response unchanged — including errors. This ticket also stands up the test seam: HTTP-boundary tests driven through the app, with an injectable fake Upstream. After this, any OpenAI-compatible Client pointed at the Bridge works normally.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] The Bridge starts from configuration covering upstream base URL, bind address, and port.
- [x] Any request is forwarded to the Upstream and its status, headers, and body are returned to the Client byte-for-byte unchanged.
- [x] Error responses (4xx/5xx) pass through with their original status, headers, and body.
- [x] HTTP-boundary integration tests run against an injected fake Upstream and assert only on returned bytes (no assertions on internal functions).

## Comments

- Verified done: `tests/test_passthrough.py`.
