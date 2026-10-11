# Purging a Conversation rewrites the log

Deleting a Conversation must remove its content for real, not merely hide it, so Purge is the one deliberate exception to the append-only rule: it excises the branch's Records from `exchanges.jsonl` (via an atomic temp-file rewrite) and then rebuilds every derived view from what remains. Because each Record already carries a unique `id` and replay attributes each one to the Conversation `(key, branch)` it built, the deleted branch's records — its chat Records and any of its rename Records — can be identified exactly and dropped. A later chat matching the purged key is a brand-new Conversation, so deletion leaves no lingering effect.

## Considered Options

- **Excise the records from the log** (chosen): content genuinely disappears; the single source of truth stays the single source of truth.
- **Soft-delete / tombstone**: keep the records and hide the Conversation. Cheap, but the content is still in the log, which fails the owner's actual goal of making old material gone.
- **Sidecar "deleted" list**: a second source of truth that must be kept in sync with the log and can drift — the same drift ADR 0002 rejected for names.
- **Rewrite only the rendered views**: leaves the authoritative log intact, so the next rebuild simply resurrects the deleted Conversation.

## Consequences

The append-only invariant now has a named exception, so anything that assumes the log only ever grows must account for the rewrite; the chat-traffic append path itself is untouched and stays append-only. Purge is per selected branch: because a branch is positional and derived, purging one renumbers later branches and may merge them, which is accepted for now, and the list is refreshed after the delete. Purge removes lines — it is **not** secure erase, and gives no guarantee that the records are scrubbed from backups or the OS. Editing rendered Markdown does not feed back into the log (see ADR 0002), so the derived `.md` files are disposable output that a rebuild merely omits once the records are gone.
