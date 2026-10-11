# 13: Deduplicate folder record builders and persist calls

**What to build:** Tidy two duplicated shapes introduced with Conversation folders, flagged by `/code-review` (no hard standard violated; both are judgement calls).

**Blocked by:** None.

**Status:** done

- [x] `models.py`: the five `build_folder_*` builders re-spell the same envelope (`id`/`owner`/`ts`/`kind=FOLDER_KIND`/`op`); collapse to one parameterised builder
- [x] `app.py`: the folder endpoints repeat `build → async with write_lock: await store.append(r); index.apply(r)`; route them through the existing `persist()` helper
- [x] No behaviour change; existing tests stay green

## Comments

- Also noted by review: `gui.py renderFolder` vs `renderNode` build near-identical DOM, and `folderPath` re-implements `markdown._live_parent`. Consider folding into this ticket if cheap.
- **Resolved:** the Python duplication is gone (`build_folder` + `persist`). The GUI note was assessed and declined: `renderFolder` (Conversations, with drag-drop and recursive folder nodes) and `renderNode` (EPUB files, with convert/move/download actions) share only the generic `<details>/<summary>` shape, not their logic; `folderPath` walks the live in-browser folder map while `_live_parent` resolves tombstones server-side — different inputs, different rules. Forcing them together would be speculative generality, so they are left as they are.
- One nuance flagged by `/code-review`: `persist()` now calls `index.apply(record)` for every write, so `other` Records also advance the index's internal `_seq`. That counter only orders rename/folder Records relative to each other, and every write increments it monotonically, so relative ordering is unchanged — no observable behaviour difference. Kept as is for a single, uniform write path.
