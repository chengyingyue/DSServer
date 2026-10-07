# 02: Conversation Names end-to-end

**What to build:** The owner can give a Conversation a human-readable name through a web page, and the name becomes the Conversation's Markdown filename. The name is persisted as a Record in the Facts Store, so it survives a full rebuild and a restart; rendering never overwrites a name the owner chose. This ticket also establishes the shared static-HTML GUI shell (a single page served by the Bridge that lists Conversations) that later EPUB work hangs off.

**Blocked by:** 01.

**Status:** ready-for-agent

- [x] A page is served at the Bridge root listing all Conversations (name, date, turn count).
- [x] Renaming a Conversation persists a rename Record in the Facts Store referencing the Conversation by identity.
- [x] After rename, the Conversation's Markdown file appears under the new name and the old filename is gone; the index reflects the new name.
- [x] Running a full rebuild, and restarting the server, preserves the owner's chosen name.
- [x] Rendering never overwrites an owner-chosen name with a derived one; Conversations without a rename keep their derived `{date}-{slug}` filename.
- [x] A rename immediately rebuilds only the affected Conversation file and the index.
- [x] The rename Record is an event (`{kind:"rename", key, name, ts}`), and applying multiple renames to one Conversation honours the latest.
- [x] All existing tests still pass.

## Final Record shape

A Conversation's true identity is `(key, branch)`: one `key` can have several branch
Conversations with distinct files, so `key` alone is ambiguous. The rename Record
therefore carries a branch discriminator:

```json
{"id": "...", "owner": "local", "ts": "...", "kind": "rename", "key": "<sha1>", "branch": 0, "name": "My Maths Notes"}
```

`branch` is the index of the Conversation within its `key` (0 for the original, 1 for
the first fork, ...), which is stable across log replay because branches are numbered in
order of first appearance. The latest rename for a given `(key, branch)` wins by `ts`.
Records stay events: a later rename supersedes an earlier one, so compaction may drop the
superseded ones safely.

