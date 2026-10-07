# 04: Build an EPUB from selected Conversations

**What to build:** The owner selects several Conversations in the GUI and gets one EPUB containing their contents, written to `data/epub/out/`. The EPUB is built in pure Python (no pandoc or other external ebook tool), reusing the EPUB packaging machinery established by conversion.

**Blocked by:** 03.

**Status:** ready-for-agent

- [ ] Selecting Conversations in the GUI builds a single EPUB containing their rendered contents.
- [ ] The built EPUB is a valid zip whose `mimetype` is the first entry and stored uncompressed, and contains the standard container/OPF structure plus one or more content documents.
- [ ] The book's title/ordering reflects the selected Conversations.
- [ ] Building does not modify the Facts Store or the rendered `conversations/` files.
- [ ] No external ebook tool is required at runtime.
- [ ] All existing tests still pass.
