# Bridge is a transparent reverse proxy

The owner needs to observe, filter, modify, and persist traffic between LLM clients and the provider. We decided to implement the Bridge as a transparent HTTP reverse proxy that clients point their base URL at, rather than as an SDK/library wrapper or a bespoke API. This works with any OpenAI-compatible client with zero per-client integration, and keeps the Upstream credential on the passthrough path so the Bridge never holds it.

## Considered Options

- **Transparent reverse proxy** (chosen): any OpenAI-compatible client changes one setting; the Bridge sees raw HTTP.
- **SDK / library wrapper**: requires modifying each client's code, and only works for clients we control.
- **Bespoke Bridge API**: clients must adopt a new interface, defeating the "drop-in" goal.

## Consequences

Because responses may be streamed (SSE), in-flight response rewriting is constrained; the Bridge will tee the stream (passthrough + accumulate) and defer response-side mutation.
