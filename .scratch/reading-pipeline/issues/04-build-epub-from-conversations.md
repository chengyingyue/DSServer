# 04: Build an EPUB from selected Conversations

**What to build:** The owner selects several Conversations in the GUI and gets one EPUB containing their contents, written to `data/epub/out/`. The EPUB is built in pure Python (no pandoc or other external ebook tool), reusing the EPUB packaging machinery established by conversion.

**Blocked by:** 03.

**Status:** resolved

- [x] Selecting Conversations in the GUI builds a single EPUB containing their rendered contents.
- [x] The built EPUB is a valid zip whose `mimetype` is the first entry and stored uncompressed, and contains the standard container/OPF structure plus one or more content documents.
- [x] The book's title/ordering reflects the selected Conversations.
- [x] Building does not modify the Facts Store or the rendered `conversations/` files.
- [x] No external ebook tool is required at runtime.
- [x] All existing tests still pass.

## Implementation notes

`src/dsserver/build.py` builds an EPUB 2.0 book from selected Conversations in pure
Python. Each Conversation becomes one XHTML content document (`OEBPS/chapterN.xhtml`)
in the selected order, produced by walking its Rendered View Markdown into headings,
paragraphs, blockquotes and code blocks. The book title is the caller's `title` when
given, otherwise the first Conversation's label (`name or title`) plus a count.

Packaging reuses the conversion path: the builder writes `mimetype`, `META-INF/container.xml`,
`OEBPS/content.opf` and `OEBPS/toc.ncx` into a staging directory, then calls the shared
`epub.repack_epub` so both conversion and building emit identically shaped zips. Output
lands in `data/epub/out/` with a `sanitize_stem`-derived, collision-free filename.

`POST /api/epub/build` accepts `{"conversations": [{"key", "branch"}, ...], "title": ...}`,
resolves each `(key, branch)` against the in-memory `ConversationIndex`, and responds with
`{"output", "title"}`. Unknown Conversations return 404, an empty selection 400. The route
sits ahead of the catch-all proxy and never writes to the Facts Store or `conversations/`.
