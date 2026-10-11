# Degrade styles for the owner's faulty e-reader

Conversion exists to make books render on the owner's e-reader, whose renderer is defective: it ignores CSS-driven italics, does not draw strikethrough, and does not display `<hr>`. Rather than depend on the device to render rich formatting, conversion degrades it to plain-text marks the device is guaranteed to show — italics become `*…*`, strikethrough becomes `~~…~~`, and `<hr>` becomes a literal `---` line — while bold, which the device does render, is preserved. The goal is legibility on one specific device, not standards-correct output.

## Considered Options

- **Degrade to plain-text marks** (chosen): replace style-dependent rendering with characters the device always shows, so emphasis survives even when the renderer does not cooperate.
- **Rely on the device's built-in rendering**: the starting assumption, but the renderer silently drops italics, strikethrough and horizontal rules, losing meaning the source expressed.
- **Rewrite the CSS so the device renders it**: no CSS fix helps, because the device does not act on CSS for these features; the failure is in the renderer, not the stylesheet.
- **Keep semantics and accept the loss**: leaves italic/struck text visually indistinguishable from body text, which is worse than a visible textual mark.

## Consequences

Conversion is a **compatibility patch, not a content reflow**: text and structure are otherwise left as they were, and only the style layer is translated. The device itself is not in the repo, so the requirements it embodies — "no CSS italics, no strikethrough, no rules" — are invisible in the code; without this record a future reader would reasonably read `*…*`/`~~…~~` substitution as a bug and "fix" it back to `<em>`/`<strike>`. Bold is the deliberate exception, and CSS fallbacks are injected to cover rules the device drops. The same reader-compatibility motive surfaces in the generated books (bounded content documents, no external DTD, explicit charset) — see issues 08 and 09 under `.scratch/reading-pipeline/issues/` and the commits that resolved them.
