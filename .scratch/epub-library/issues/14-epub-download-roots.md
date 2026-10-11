# 14: Reconcile EPUB file-download roots with the spec

**What to build:** Decide whether `GET /api/epub/file` should serve files from `inbox` as well as `out`. The spec scoped download to "any EPUB under `out`"; the implementation generalises it to `inbox` too (the GUI offers a Download action on inbox files and folders). Either narrow the endpoint back to `out`, or update the spec to record the intentional generalisation.

**Blocked by:** None.

**Status:** needs-triage

- [ ] Confirm intended scope of EPUB file download
- [ ] Either restrict `roots=("out",)` or amend the spec
- [ ] Update the `/api/epub/file` and GUI tests to match

## Comments

- Raised by `/code-review` against spec line 190.
