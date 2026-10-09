# 09: Make built EPUBs render on mobile readers

**What to build:** Built EPUBs opened but rendered blank / kept loading on a phone, while converted EPUBs (from real books) rendered fine. Comparison with the working reference showed the built books were a single enormous content document, and carried an external XHTML DTD that a reader may try to fetch offline and stall on. Emit each book the way real EPUBs (and the working converted output) are shaped: many bounded content documents, no external DOCTYPE, a stylesheet, plus the charset declaration from the previous fix.

**Blocked by:** 08.

**Status:** resolved

- [x] Built books split into multiple content documents, each bounded in size, instead of one giant document.
- [x] Content documents carry no external `<!DOCTYPE>` (nothing for an offline reader to fetch and hang on).
- [x] A stylesheet is linked from every content document and listed in the package, letting long content wrap.
- [x] Fenced code stays balanced across every split document; every content document, the package, NCX and container parse as well-formed XML.
- [x] All existing tests still pass.
