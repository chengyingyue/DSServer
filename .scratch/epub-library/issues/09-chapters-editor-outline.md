# 09: Chapters and editor outline

**What to build:** Building splits the document into chapters at every H1 heading and at an explicit `<!-- chapter -->` separator. The editor shows a chapter outline and offers an "insert chapter break" button. Book title precedence is explicit title → Work Copy name → first heading.

**Blocked by:** 08.

**Status:** done

- [x] Build splits at H1 and at `<!-- chapter -->`
- [x] Title precedence is explicit → Work Copy name → first heading
- [x] The editor shows a chapter outline (links that move the caret; not yet collapsible — see 11)
- [x] ~~The editor offers an insert-chapter-break button~~ — dropped by owner request: an explanatory note replaces it (type `#` or `<!-- chapter -->` directly)
- [x] A size cap is retained within a chapter for mobile readers

## Comments

- The "insert chapter break" button was removed in favour of a one-line hint, per the owner's request. The collapsible form of the outline was split out to ticket 11.
