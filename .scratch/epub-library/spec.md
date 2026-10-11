# EPUB Library, Conversation Purge, Work Copy naming & chapters

Status: ready-for-agent

## Problem Statement

As the owner, I run the Bridge and use its web GUI as my one page for reading
and e-book production. Four things get in the way:

1. **I can't delete Conversations I no longer want.** Old, useless threads pile
   up in the list forever. I want a Delete action beside View and Rename.
2. **The page is laid out in a stale order.** The sections should read
   EPUB → Conversations → Work copy, and each section should fold away when I'm
   not using it.
3. **My EPUBs live in folders on disk, but the GUI can't see them.** I already
   organise sources into nested folders, but the page shows a flat list and can
   only convert whole files. I want to create/rename/delete folders, convert a
   folder recursively, download a folder, and delete or move files.
4. **Work copies are nameless and always come out as one undivided blob.** I
   address them by an opaque hex id in a text box, and the built EPUB is a
   single undivided document. I want to name a Work Copy and split it into
   chapters.

Separately, the Conversation View shows raw Markdown text; I want it rendered.

## Solution

Extend the existing single-page GUI and its HTTP API:

- **Conversation Purge.** A Delete action removes a Conversation for real by
  rewriting the Facts Store to excise its records, then rebuilding the derived
  views. Old content genuinely disappears; if a later chat matches a purged key
  it becomes a brand-new Conversation.
- **Reordered, collapsible page.** Three collapsible sections in the order
  EPUB → Conversations → Work copy.
- **EPUB Library.** The EPUB section becomes a file browser over `data/epub/`,
  showing inbox/out/work as its top-level folders. It supports folder
  create/rename/delete (recursive), recursive convert, folder download, and file
  move/delete — with the conversion output mirroring the source folder layout.
- **Named Work Copies with chapters.** Work Copies get human names; the built
  EPUB is split into chapters at H1 headings (and at an explicit manual
  separator), with the Work Copy name as the default book title.
- **Rendered Conversation View.** The View dialog renders Markdown as HTML
  (server-side); the Work Copy editor stays plain text.

## User Stories

1. As the owner, I want to delete an old Conversation from the list, so that
   stale threads stop cluttering my reading view.
2. As the owner, I want deleting to actually remove the Conversation's chat
   records from the Facts Store, so that the content is gone rather than merely
   hidden.
3. As the owner, I want delete to be a deliberate, confirmed action, so that I
   never lose a Conversation by a stray click.
4. As the owner, I want the deletions to survive a restart and a rebuild, so
   that what I deleted stays deleted.
5. As the owner, I want the Conversation's rendered Markdown file removed too
   when I delete it, so that the derived views match the log.
6. As the owner, I want a later chat that matches a deleted Conversation's key
   to appear as a new Conversation, so that deletion has no lingering effect.
7. As the owner, I want the page ordered EPUB → Conversations → Work copy, so
   that the sections appear in the order I actually use them.
8. As the owner, I want each of the three sections to fold and unfold, so that I
   can focus on one at a time.
9. As the owner, I want the EPUB section to show my real folder structure, so
   that the folders I make on disk become usable in the GUI.
10. As the owner, I want to create a folder, so that I can group EPUBs without
    leaving the page.
11. As the owner, I want to rename a folder, so that I can fix its name.
12. As the owner, I want to delete a folder and everything inside it (after a
    confirmation), so that I can clear out material I no longer need.
13. As the owner, I want to convert a single EPUB, so that I get an
    e-reader-friendly copy in the out area.
14. As the owner, I want to convert a whole folder recursively, so that I can
    process a batch in one action.
15. As the owner, I want converted output to mirror the source folder layout, so
    that files with the same name in different folders don't collide and I can
    find them.
16. As the owner, I want to download a single file, so that I can move it to my
    e-reader.
17. As the owner, I want to download every file in a folder, so that I can grab
    a whole set at once.
18. As the owner, I want to move a file between folders within inbox or out, so
    that I can re-organise without a file manager.
19. As the owner, I want to delete a file, so that I can discard material I don't
    need.
20. As the owner, I want folder/file names to allow my usual non-ASCII
    characters, so that names stay readable.
21. As the owner, I want the GUI to refuse unsafe paths, so that a mistyped name
    can never reach outside the EPUB area.
22. As the owner, I want to give a Work Copy a meaningful name, so that I can
    find it later instead of memorising a hex id.
23. As the owner, I want to see my Work Copies listed by name, so that I can load
    one without typing an id.
24. As the owner, I want to rename a Work Copy, so that I can correct its name.
25. As the owner, I want the Work Copy name to become the built EPUB's title and
    filename by default, so that the output is identifiable.
26. As the owner, I want to override the title at build time, so that I can
    fine-tune the output without renaming the copy.
27. As the owner, I want the built EPUB split at each H1 heading, so that each
    top-level section becomes its own chapter in my e-reader.
28. As the owner, I want to force a chapter break anywhere with an explicit
    marker, so that I can control chaptering beyond the headings.
29. As the owner, I want to see the current chapter outline while editing, so
    that I can tell how the book will be divided.
30. As the owner, I want to jump to a chapter from the outline, so that I can
    navigate a long Work Copy.
31. As the owner, I want an explicit way to see and edit the whole Work Copy as
    chapters (fold per chapter), so that I can work chapter by chapter.
32. As the owner, I want the Conversation View to render Markdown, so that I can
    read formatting instead of raw source.
33. As the owner, I want the Work Copy editor to stay plain text, so that editing
    stays predictable and unformatted.
34. As the owner, I want all of this on the same page and same process, so that I
    keep running one tool.
35. As the owner, I want no node/npm build chain or CDN dependency, so that the
    page keeps working offline over Tailscale/LAN.

## Implementation Decisions

- **Two fact sources, unchanged and not subordinate** (from the reading pipeline
  spec): Conversations derive from the append-only Facts Store; the EPUB Library
  owns the files under `data/epub/`. The EPUB Library is inputs/working data plus
  disposable products; nothing there is authoritative state.
- **Purge rewrites the Facts Store.** Each Record already carries a unique `id`.
  During replay the index attributes each Record to the Conversation
  `(key, branch)` it built. Delete resolves that branch's Record ids, removes
  exactly those lines (chat Records and any rename Records for that branch), and
  atomically rewrites `exchanges.jsonl` (temp file + replace). The index and all
  derived views (`conversations/*.md`, `index.md`) are then rebuilt from the
  remaining Records. This is the one deliberate exception to append-only.
- **Purge granularity is per selected branch.** Because a branch is positional
  and derived, purging a branch renumbers later branches and may merge them;
  this is accepted. The list is refreshed after delete. A later chat matching the
  purged key is a new Conversation.
- **The Store gains a single rewrite primitive** (remove a set of Record ids,
  atomically), sitting beside the existing append. The append-only path for chat
  traffic is untouched.
- **Conversation View renders server-side.** The content endpoint returns an
  additional rendered-HTML field. Rendering reuses the existing Markdown→XHTML
  converter (extended just enough for the reading view), so there is no client
  library, CDN, or build chain. Only the Conversation View uses it; the Work Copy
  editor stays plain text.
- **EPUB Library is one rooted tree with three fixed roots** (`inbox`, `out`,
  `work`) under `data/epub/`. A "folder" is a real directory. Conversations are
  **not** part of this tree — they remain their own list section (their `.md` are
  disposable derived views with identity `(key, branch)`, not filenames).
- **Root separation is preserved:** `inbox` = sources, `out` = products,
  `work` = Work Copy drafts. Files may be moved **within** `inbox` or **within**
  `out`, never between them and never into/out of `work` (Work Copies are
  addressed by id through their store, not by path).
- **Path safety at the boundary.** A single resolver maps a requested relative
  path to an absolute path and rejects absolute paths, `..` segments, drive
  letters, and anything resolving outside `data/epub/`; write operations are
  further constrained to `inbox`/`out`. Non-ASCII names are allowed.
- **Recursive convert mirrors structure.** Converting a file writes the result
  to the same relative path under `out/`; converting a folder walks it and
  produces the mirrored tree. Name collisions are resolved the existing way
  (numbered suffixes). Inbox scanning becomes recursive.
- **Folder download uses individual browser downloads** (no zip), as chosen;
  preserving folder structure depends on the browser being set to ask where to
  save each file. Single-file download uses the existing download mechanism.
- **Work Copies become named.** The Work Copy store keeps a name for each copy
  (name defaulted from the copy's first heading, renameable, persisted beside the
  copy because Work Copies are disposable and outside the Facts Store). The name
  is used as the built EPUB's title/filename unless overridden at build time.
- **Chaptering is deterministic, not size-driven.** The builder splits the
  document into chapters at every H1 heading and at an explicit manual separator
  token (a lone `<!-- chapter -->` line). The previous fixed character-chunking is
  retained only as a safety cap *within* a chapter for mobile-reader
  compatibility. Book title precedence: explicit build title → Work Copy name →
  document's first heading.
- **GUI shape:** three collapsible sections; the EPUB section renders the tree
  with inline per-node actions; destructive actions (recursive folder delete,
  Conversation purge) require an in-page confirmation; the Work Copy editor shows
  a collapsible chapter outline plus an "insert chapter break" button.
- **API contracts (new/changed, on the existing HTTP boundary):**
  - `DELETE /api/conversations/{key}?branch=N` → purge the branch; returns the
    number of Records removed.
  - `GET /api/conversations/{key}/content?branch=N` → additionally returns
    `html`.
  - `GET /api/epub/tree` → nested nodes (`path` relative-posix, `name`, `type`,
    `children`) for the three roots.
  - `POST /api/epub/folder` `{path}` → create folder.
  - `POST /api/epub/folder/rename` `{from, to}` → rename/move a folder.
  - `DELETE /api/epub/folder?path=...` → recursively delete a folder.
  - `POST /api/epub/move` `{from, to}` → move a file within inbox or out.
  - `DELETE /api/epub/file?path=...` → delete a file.
  - `POST /api/epub/convert` `{path}` → convert a file or a folder recursively.
  - `GET /api/epub/file?path=...` → download any EPUB under `out` (generalises
    the current out-only download); folder download is driven client-side.
  - `POST /api/epub/upload?name=...&dir=...` → upload into a chosen folder.
  - `GET /api/epub/work` → list Work Copies `{id, name}`.
  - `POST /api/epub/work` `{conversations, name?}` → create a named copy.
  - `PATCH /api/epub/work/{id}` `{name}` → rename a copy.
  - `POST /api/epub/build` `{work?, conversations?, title?}` → chapter-split
    build (unchanged shape).
- **Modules (by responsibility):** log Store (add atomic rewrite), Conversation
  index/replay (attribute Record ids to branches; purge), Markdown rendering
  (server-side HTML for the View), EPUB module (tree listing, folder CRUD,
  recursive convert, move/delete, path resolver), Work Copy store (names), build
  module (heading/separator chaptering), and the GUI layer (layout, tree, forms).

## Testing Decisions

- **A good test drives only the app's HTTP interface** and asserts (a) the
  response, (b) the contents of `exchanges.jsonl`, and (c) the artifacts on disk
  under `data/`. Never assert internal functions.
- **The single seam is the existing HTTP boundary** — the fake Client via
  `httpx.ASGITransport` and the fake Upstream via `httpx.MockTransport` in
  `tests/conftest.py`. No new seam is introduced.
- **Behaviours covered through that seam:**
  - Purge: after `DELETE`, the Conversation's chat records are gone from the log,
    its `.md` is gone, `index.md` no longer lists it; a restart rebuild keeps it
    gone; a subsequent matching chat yields a new Conversation.
  - Tree: `GET /api/epub/tree` reflects nested folders (including non-ASCII
    names); unsafe paths are refused.
  - Folder CRUD: create/rename/delete, with recursive delete removing contents.
  - Recursive convert: converting a nested folder produces the mirrored structure
    under `out/` and valid EPUBs (assert with `zipfile`: `mimetype` first and
    stored, `container.xml`/OPF/target XHTML present).
  - Move/delete file: within-root moves succeed; cross-root or into `work` is
    refused.
  - Work Copies: create with a name, list by name, rename; built EPUB title
    follows the name and is overridable.
  - Chaptering: an H1-split and a `<!-- chapter -->`-split document both produce
    one XHTML document per chapter with matching NCX points.
  - View: the content endpoint returns populated `html`.
- **Prior art:** the existing suites `test_epub_conversion.py`,
  `test_epub_build.py`, `test_conversation_names.py`, `test_downloads.py`,
  `test_work_copies.py`, `test_incremental_render.py` — same seam, same style.

## Out of Scope

- Writing the two ADRs (EPUB converter rationale; Purge) — a **separate
  workstream** (handoff issued), not this feature.
- Secure erase / shredding of purged records; purge removes lines, it does not
  guarantee scrubbing from backups or the OS.
- Hardening branch identity (stable branch ids). Per-branch purge's renumbering is
  accepted for now.
- Log compaction/rotation beyond the purge rewrite.
- A zip/streamed folder download (folder download is individual files by choice).
- Editing or moving **Conversations** as files on disk; their identity stays
  `(key, branch)` and their `.md` stay derived.
- Multi-user auth; Docker; HTTPS/Tailscale setup; front-end frameworks; any
  external e-book tool (pandoc).

## Further Notes

- Domain vocabulary is `GLOSSARY.md`: Record, Facts Store, Conversation,
  Conversation Name, Rendered View, EPUB Pipeline, Work Copy; and
  `docs/adr/0002-log-is-the-single-source-of-truth.md` for the log-as-truth rule
  that Purge deliberately excepts.
- The parallel handoff for the ADRs lives in the OS temp directory
  (`handoff-adr-epub-pipeline.md`).
- `data/epub/inbox/` already contains nested folders (e.g. `ao3/...`) that the
  current flat listing ignores — those become visible with the tree.
