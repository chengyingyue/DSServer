# 14: Reconcile EPUB file-download roots with the spec

**What to build:** Decide whether `GET /api/epub/file` should serve files from `inbox` as well as `out`. The spec scoped download to "any EPUB under `out`"; the implementation generalises it to `inbox` too (the GUI offers a Download action on inbox files and folders). Either narrow the endpoint back to `out`, or update the spec to record the intentional generalisation.

**Blocked by:** None.

**Status:** done

- [x] Confirm intended scope of EPUB file download
- [x] Either restrict `roots=("out",)` or amend the spec
- [x] Update the `/api/epub/file` and GUI tests to match

## Comments

- Raised by `/code-review` against spec line 190.
- **Decision:** keep the generalisation. The GUI deliberately offers Download on both `inbox` and `out` files and folders (grabbing a source EPUB is a real use), so narrowing the endpoint would strip a feature. Amended the spec's API line to record download from `inbox` or `out`, with `work` deliberately excluded (Work Copies are addressed by id, not path). Added a test locking that scope: an inbox path downloads, a `work` path is refused with 400. The GUI already wired Download for both roots, so no GUI change was needed; `test_the_gui_offers_folder_and_file_download` now asserts the file-download wiring too.
