# 13: Deduplicate folder record builders and persist calls

**What to build:** Tidy two duplicated shapes introduced with Conversation folders, flagged by `/code-review` (no hard standard violated; both are judgement calls).

**Blocked by:** None.

**Status:** ready-for-agent

- [ ] `models.py`: the five `build_folder_*` builders re-spell the same envelope (`id`/`owner`/`ts`/`kind=FOLDER_KIND`/`op`); collapse to one parameterised builder
- [ ] `app.py`: the folder endpoints repeat `build → async with write_lock: await store.append(r); index.apply(r)`; route them through the existing `persist()` helper
- [ ] No behaviour change; existing tests stay green

## Comments

- Also noted by review: `gui.py renderFolder` vs `renderNode` build near-identical DOM, and `folderPath` re-implements `markdown._live_parent`. Consider folding into this ticket if cheap.
