# 12: In-page confirmation dialogs

**What to build:** The destructive actions that the spec and tickets asked to confirm "in-page" currently use the browser's blocking `window.confirm`, not an in-page `<dialog>` like the folder and render pickers. Replace the `window.confirm` calls with in-page confirmation dialogs for consistency.

**Blocked by:** None.

**Status:** done

- [x] Purging a Conversation confirms via an in-page `<dialog>`, not `window.confirm`
- [x] Deleting an EPUB folder confirms via an in-page `<dialog>`
- [x] Deleting a file (if confirmed) follows the same pattern
- [x] Cancel leaves the resource untouched

## Comments

- Raised by `/code-review` against spec lines 174-176 and tickets 02 ("confirmed in-page") and 05 ("after an in-page confirmation").
- Done: a shared `confirmDialog(message)` in `app.js` drives a single `<dialog id="confirm-dialog">`; the four `window.confirm` sites (Conversation purge, Conversation folder delete, EPUB folder delete, EPUB file delete) now await it. Cancel, Escape (the dialog's `close` event), and the Cancel button all resolve `false` and leave the resource untouched. A GUI test asserts the dialog is present and that `window.confirm` is gone from the served page.
