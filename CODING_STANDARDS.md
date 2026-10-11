# Coding standards

Judgement calls for this repo — rules a machine can't enforce, so the reviewer applies them. Anything a tool already enforces (typing via mypy, formatting, the GUI's offline/JS-syntax rules via `scripts/check.py`) is deliberately **not** repeated here.

Run all checks before committing:

```
uv run python scripts/check.py     # pytest + mypy + GUI JS syntax
```

Enable the pre-commit hook once per clone:

```
git config core.hooksPath .githooks
```

## Persistence

- **Authoritative state lives only in the log** (`exchanges.jsonl`) as Records — never a sidecar file, never derived from filenames (ADR 0002). A new persistent concept becomes a Record `kind` (and an `op` if it has variants), replayed in order; for folders and render modes, see ADR 0005.
- **Record builders share one envelope.** Do not re-spell `id` / `owner` / `ts` / `kind`; factor a shared builder when a second op needs the same shape.

## Filesystem

- **Resolve roots at the boundary.** `resolve_epub_path` returns absolute paths; a caller that keeps its own root relative will blow up on `relative_to`. Normalise to one absolute base and stay on it. (This is the class of bug behind the relative-`store_dir` convert crash.)

## GUI

- **Source layout:** the GUI lives in `src/dsserver/gui/` as `index.html`, `app.css` and `app.js`. `__init__.py` assembles them into a single `INDEX_HTML` at import, so the page is still served as one offline document. Edit the source files, never a copy.
- **The GUI is one offline page.** Icons are inline SVG; do not reintroduce a `<use>`/sprite, a CDN, a client-side framework, or a build chain. `scripts/check.py` fails the build if the embedded JS references an external URL.
- **Bump the `gui vN` tag** in the page header on every GUI change. It is how a running build is identified — a stale server process once served old HTML and the tag is what caught it.
- **Confirm destructive actions in-page** with a `<dialog>`, not `window.confirm` (purge, folder/file delete). Keep it consistent with the folder and render pickers.
