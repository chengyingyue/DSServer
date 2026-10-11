# 04: EPUB Library tree (read-only)

**What to build:** The EPUB section shows the real folder structure under `data/epub/`, with `inbox`, `out` and `work` as its top-level folders, instead of two flat lists. Read-only first — browsing only.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `GET /api/epub/tree` returns nested nodes (`path`, `name`, `type`, `children`) for the three roots
- [x] The GUI renders collapsible folders and files, preserving non-ASCII names
- [x] Paths resolving outside `data/epub/` are refused
