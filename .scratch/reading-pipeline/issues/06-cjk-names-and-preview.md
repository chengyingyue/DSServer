# 06: Readable filenames (CJK) and in-GUI Conversation preview

**What to build:** Two things that make it possible to tell what a Conversation is about without opening files on disk. (A) Derived filenames keep non-ASCII (e.g. CJK) characters instead of falling back to an opaque hash, so `data/conversations/` names are readable. (B) In the GUI, clicking a Conversation opens a read-only preview of its rendered content, so the owner can "click in" without leaving the page.

**Blocked by:** 05.

**Status:** resolved

- [x] A Conversation whose first user message is CJK gets a readable filename containing those characters (e.g. `2026-10-07-你好世界.md`), not a hash.
- [x] Filenames remain safe (no path/illegal characters) and unique.
- [x] An API endpoint returns a Conversation's rendered content by `(key, branch)`.
- [x] The GUI shows a per-Conversation preview (click the name or a View button) rendering that content; unknown Conversations error cleanly.
- [x] All existing tests still pass.
