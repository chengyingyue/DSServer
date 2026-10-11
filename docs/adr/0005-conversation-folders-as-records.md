# Conversation folders and their render mode are Records in the log

Conversation folders — a nested, user-made tree used to organise Conversations in the GUI — and each folder's Markdown **render mode** are persisted as Records in the same append-only log, not as a sidecar tree or as part of a Conversation's own records. A folder is created, renamed, deleted, has a Conversation assigned to it, or has its render mode set, all as `kind: "folder"` Records distinguished by an `op` field. Replay folds them into the index exactly like renames, so `folders()`, the folder a Conversation sits in, and its effective render mode are all reconstructed from the log alone.

A **Render Mode** is per-folder: `normal` renders fenced code blocks as code; `plain_code` ignores the ` ``` ` fences and renders the fenced content as ordinary Markdown. It is a property of the folder, not of a Conversation, and a child folder with no mode of its own **inherits** its nearest ancestor's, defaulting to `normal`. Conversations that are not filed (Unfiled) are always `normal`.

## Considered Options

- **Folder ops as Records in the log** (chosen): one source of truth; folders, assignments and modes replay in order alongside chat and rename Records, and survive `render` and restarts with no extra state to keep in sync.
- **A sidecar tree file** (e.g. `.folders.json`): easy to write, but a second source of truth that can drift from the log — the same drift ADR 0002 rejected for names.
- **Store the folder on the Conversation's chat Record**: would rewrite chat traffic (append-only), and cannot express an empty folder or a folder whose mode changes without a Conversation in it.
- **Derive folders from filenames**: loses nesting, empty folders, and the mode, and couples organisation to the disposable Rendered View.

## Consequences

The log's Record vocabulary grows by one kind with five ops (`create`/`rename`/`delete`/`assign`/`render`). Deleting a folder is a tombstone in the log: its Conversations and sub-folders fall back to its nearest live ancestor (or Unfiled), which keeps the append-only invariant intact — only Purge (ADR 0004) excises lines. A folder's render mode is inherited down the tree, so changing an ancestor's mode changes what descendants render without touching them. Because identity is positional and derived (ADR 0004), an empty folder exists only as long as its `create` Record stands.
