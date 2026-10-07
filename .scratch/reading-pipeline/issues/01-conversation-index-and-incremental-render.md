# 01: Conversation index and incremental rendering

**What to build:** Adding a message to a Conversation no longer rewrites the whole reading view. Only that Conversation's Markdown file and the index are written; every other file is left untouched (same content, same timestamp). The server maintains an in-memory index keyed by Conversation identity, rebuilt from the Facts Store on startup, so rendering is O(one Conversation) per message instead of O(all Conversations). This removes the "all files updated at once, cost grows with history" symptom.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] After a chat request, only the affected Conversation's Markdown file and the index change on disk; other Conversation files keep identical contents and mtime.
- [ ] A rendered file whose content has not changed is not rewritten (its mtime does not move).
- [ ] The in-memory index is built by replaying the Facts Store at startup and is not persisted anywhere (it is a rebuildable cache, never a second source of truth).
- [ ] Existing Markdown rendering rules, grouping rules, filenames, and the index listing are unchanged.
- [ ] `render` (full rebuild from the Facts Store) still produces the same output as on the previous revision.
- [ ] All existing tests still pass.
