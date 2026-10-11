# 12: In-page confirmation dialogs

**What to build:** The destructive actions that the spec and tickets asked to confirm "in-page" currently use the browser's blocking `window.confirm`, not an in-page `<dialog>` like the folder and render pickers. Replace the `window.confirm` calls with in-page confirmation dialogs for consistency.

**Blocked by:** None.

**Status:** ready-for-agent

- [ ] Purging a Conversation confirms via an in-page `<dialog>`, not `window.confirm`
- [ ] Deleting an EPUB folder confirms via an in-page `<dialog>`
- [ ] Deleting a file (if confirmed) follows the same pattern
- [ ] Cancel leaves the resource untouched

## Comments

- Raised by `/code-review` against spec lines 174-176 and tickets 02 ("confirmed in-page") and 05 ("after an in-page confirmation").
