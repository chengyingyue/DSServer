# 03: EPUB conversion end-to-end

**What to build:** The owner can take an existing EPUB and get back a copy tuned for their e-reader (italics/strikethrough as text marks, bold retained, `<hr>` as text, fallback CSS, TOC heading rules). They can drop an EPUB into `data/epub/inbox/` on the computer, or upload one, then trigger conversion from the shared GUI; the result lands in `data/epub/out/`. The conversion capability already exists as a batch script and is refactored into a reusable service module behind the existing HTTP boundary.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] An EPUB placed in `data/epub/inbox/` can be converted, producing a valid EPUB in `data/epub/out/`.
- [ ] The produced EPUB is a valid zip whose `mimetype` is the first entry and stored uncompressed, and contains the standard container/OPF structure.
- [ ] The GUI offers converting a single file and scanning/processing everything in the inbox.
- [ ] The conversion logic is a reusable module (not a `__main__` batch script); the original e-reader compatibility behaviour is preserved.
- [ ] Malformed/unsupported input surfaces a clear error rather than corrupting output.
- [ ] All existing tests still pass.
