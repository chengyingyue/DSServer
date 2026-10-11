# 02: Conversation Purge (Delete)

**What to build:** A Delete action beside View and Rename removes a Conversation for real: the Facts Store is rewritten to excise that branch's chat and rename Records, then the index and derived views are rebuilt. Deletion is confirmed in-page and survives restarts and `render`.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `DELETE /api/conversations/{key}?branch=N` removes that branch's chat and rename Records from the log
- [x] The Conversation's rendered `.md` and its `index.md` entry disappear
- [x] The deletion survives a restart and a full rebuild
- [x] A later chat matching the purged key becomes a new Conversation
- [x] The GUI offers a Delete button with a confirmation
