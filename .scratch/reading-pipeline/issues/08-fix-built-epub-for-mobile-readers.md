# 08: Fix built EPUBs rejected by phone readers

**What to build:** EPUBs produced by "Build EPUB" opened on a desktop reader but not on a phone. The generated content documents declared an HTML5 `<!DOCTYPE html>` inside an EPUB 2.0 package and contained no character-set declaration, so strict/mobile readers could mis-decode (or refuse) them while desktop readers tolerated it. Emit proper EPUB2 XHTML (XHTML 1.1 doctype plus a UTF-8 `<meta http-equiv="Content-Type">`), and strip characters that are illegal in XML so a stray control character can never corrupt the whole book.

**Blocked by:** 07.

**Status:** resolved

- [x] Each built content document declares an XHTML 1.1 doctype and a UTF-8 charset meta.
- [x] Every content document, the package document, the NCX and the container parse as well-formed XML.
- [x] XML-invalid control characters in Conversation content are removed rather than producing an invalid book.
- [x] All existing tests still pass.
