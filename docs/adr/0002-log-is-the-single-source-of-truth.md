# The exchange log is the single source of truth

Every rendered artifact (per-Conversation Markdown, the index) is reconstructed from the append-only `exchanges.jsonl`. Because users can rename Conversations, and a rename is human-owned data that cannot be inferred from message content, the name is persisted as its own Record in the same log rather than kept in a sidecar file or encoded in the filename.

## Considered Options

- **Rename as a Record in the log** (chosen): keeps one source of truth; renames are replayed like anything else, in order.
- **Sidecar mapping file** (`.names.json`): simpler to write, but introduces a second source of truth that must be kept in sync with the log and can drift.
- **Filename is the identity**: let the human rename files directly and infer identity from the filesystem. Fragile — a rename severs the link to the Conversation, and regeneration either overwrites the name or spawns duplicates.

## Consequences

The log is no longer purely a record of chat traffic; it carries a small vocabulary of Record kinds. Rendering must never overwrite a user-chosen name, so a renderer cannot blindly rewrite every file — it must respect persisted names and skip unchanged output. Editing rendered Markdown does **not** feed back into the log: content edits live only in an ephemeral copy owned by the EPUB Pipeline. Renaming is an explicit application action, not a filesystem event the Bridge watches for.
