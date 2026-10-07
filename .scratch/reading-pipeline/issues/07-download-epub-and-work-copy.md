# 07: Download produced EPUBs and work copies

**What to build:** The GUI can download the things the EPUB pipeline produces. Each file in the EPUB outbox can be downloaded, and an editable work copy can be downloaded as a Markdown file. Both are served locally by the Bridge (never proxied), with safe filename handling.

**Blocked by:** 06.

**Status:** resolved

- [x] Each file listed for the EPUB outbox has a Download action that serves the file as an epub attachment.
- [x] A work copy can be downloaded as a Markdown attachment.
- [x] Unknown or unsafe names error cleanly (no path traversal); the routes are served locally, not forwarded upstream.
- [x] All existing tests still pass.
