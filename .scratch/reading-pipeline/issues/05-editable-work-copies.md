# 05: Editable work copies (generate → edit → build → discard)

**What to build:** The owner can generate an editable copy of selected Conversations, edit it (once or repeatedly) with no effect on the Facts Store or the rendered `conversations/` files, then build an EPUB from the copy and discard it. The copy is owned entirely by the EPUB Pipeline's own working area and is decoupled from the Conversation the moment it is created.

**Blocked by:** 04.

**Status:** resolved

- [x] The owner can create a work copy from selected Conversations; it lives in the EPUB Pipeline's working area and is separate from the Facts Store.
- [x] The owner can read and save the work copy's content, and may stay editing across multiple save/load cycles before building.
- [x] Editing a work copy never changes `exchanges.jsonl` or any rendered `conversations/` file.
- [x] An EPUB can be built from a work copy.
- [x] A work copy can be discarded, removing it from the working area.
- [x] A work copy, once created, bears no ongoing relationship to its source Conversations.
- [x] All existing tests still pass.
