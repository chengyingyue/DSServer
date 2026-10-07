# 02: Conversation Names end-to-end

**What to build:** The owner can give a Conversation a human-readable name through a web page, and the name becomes the Conversation's Markdown filename. The name is persisted as a Record in the Facts Store, so it survives a full rebuild and a restart; rendering never overwrites a name the owner chose. This ticket also establishes the shared static-HTML GUI shell (a single page served by the Bridge that lists Conversations) that later EPUB work hangs off.

**Blocked by:** 01.

**Status:** ready-for-agent

- [ ] A page is served at the Bridge root listing all Conversations (name, date, turn count).
- [ ] Renaming a Conversation persists a rename Record in the Facts Store referencing the Conversation by identity.
- [ ] After rename, the Conversation's Markdown file appears under the new name and the old filename is gone; the index reflects the new name.
- [ ] Running a full rebuild, and restarting the server, preserves the owner's chosen name.
- [ ] Rendering never overwrites an owner-chosen name with a derived one; Conversations without a rename keep their derived `{date}-{slug}` filename.
- [ ] A rename immediately rebuilds only the affected Conversation file and the index.
- [ ] The rename Record is an event (`{kind:"rename", key, name, ts}`), and applying multiple renames to one Conversation honours the latest.
- [ ] All existing tests still pass.
