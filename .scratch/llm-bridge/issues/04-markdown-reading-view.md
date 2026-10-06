# 04: Markdown reading view for Exchanges

**What to build:** A human-readable reading layer over the JSONL log. Each conversation becomes a Markdown file in which app-injected (system) content is clearly distinguished from human input and assistant output — the primary place the owner studies Injected Prompts. Repeated full-history requests collapse into one conversation by extending a known prefix; divergent prefixes start a new conversation file.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] Each Exchange appears in a per-conversation Markdown file named `{YYYY-MM-DD}-{slug}` (slug from the first user message, sanitized; non-ASCII/empty falls back to a short hash).
- [ ] Injected (system) messages are visually distinguished from human (user) input; assistant output is labelled.
- [ ] Reasoning content, model, token usage, and latency are shown when present.
- [ ] Requests that extend a known conversation prefix append only the delta; a divergent prefix (edit/regenerate) starts a new conversation file.
- [ ] An index file lists conversations.
- [ ] Raw SSE is never rendered.
