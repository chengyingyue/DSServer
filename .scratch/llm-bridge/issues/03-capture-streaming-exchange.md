# 03: Capture a streaming Exchange

**What to build:** A streaming chat response is relayed to the Client chunk-by-chunk as it arrives, while the Bridge simultaneously accumulates it; when the stream ends the full Exchange is persisted. Chat feel is unchanged and nothing is lost.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] Streaming chat responses are relayed to the Client chunk-by-chunk in real time, byte-faithfully.
- [ ] The full assistant message (`content`, `reasoning_content`, `tool_calls`) is reconstructed from the deltas and stored.
- [ ] Usage is taken from the final chunk before `[DONE]`.
- [ ] Raw SSE text is stored when `keep_raw_sse` is true, and omitted otherwise.
- [ ] A Client consuming the stream observes no behavioral difference from talking to the Upstream directly.
