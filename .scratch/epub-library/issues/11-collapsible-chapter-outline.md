# 11: Collapsible chapter outline

**What to build:** The Work Copy editor's chapter outline is collapsible (a `<details>` per chapter) rather than a flat list, so a long document's outline can be folded. Split out of ticket 09, whose outline landed as plain links that move the caret.

**Blocked by:** None (09 is done).

**Status:** done

- [x] The outline renders as collapsible per-chapter entries
- [x] Collapsing one chapter's outline does not affect the editor content
- [x] Outline still jumps the caret to the chapter on click

## Comments

- Implemented as a collapsible heading tree: `headingTree` parses every `#`–`######` heading into a nested structure, and `renderOutlineNode` emits a `<details>` per heading (open by default). Sub-headings nest under their chapter, so a long outline folds branch by branch. The chapter title is a link that jumps the caret; it calls `preventDefault`/`stopPropagation` so clicking the title jumps without toggling, while the disclosure marker folds. Collapsing only hides DOM — the textarea is never touched.
