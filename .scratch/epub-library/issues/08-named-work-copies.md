# 08: Named Work Copies

**What to build:** Work Copies get human names. Create one with a name (defaulted from its first heading), list them by name, and rename them. The name becomes the built EPUB's title and filename unless overridden at build time.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `POST /api/epub/work` accepts a name (defaulted from the first heading)
- [x] `GET /api/epub/work` lists copies `{id, name}`
- [x] `PATCH /api/epub/work/{id}` renames a copy
- [x] The built EPUB's title/filename use the name unless overridden
- [x] The GUI replaces the raw-id text box with a named list
