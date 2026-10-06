# 05: Rebuild Markdown from JSONL

**What to build:** A `render` command that treats JSONL as the single source of truth and regenerates every Markdown file from it, so the reading layer can be recomputed whenever rendering logic changes.

**Blocked by:** 04.

**Status:** ready-for-agent

- [ ] A `render` command regenerates all Markdown files from the JSONL log.
- [ ] Regenerated output matches what incremental writing produced for the same records.
- [ ] Markdown is treated as a derived view: running `render` never modifies the JSONL log.
