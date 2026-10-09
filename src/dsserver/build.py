from __future__ import annotations

import html
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .epub import EpubError, publish_epub, repack_epub, unique_output
from .markdown import Conversation, render_conversation, sanitize_stem

MIMETYPE = "application/epub+zip"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

_XML_INVALID_RE = re.compile(
    "[^\u0009\u000a\u000d\u0020-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]"
)


def _xml_safe(text: str) -> str:
    return _XML_INVALID_RE.sub("", text)


def _escape(text: str, quote: bool = True) -> str:
    return html.escape(_xml_safe(text), quote=quote)


STYLES_CSS = """\
body { margin: 1em; line-height: 1.5; }
pre { white-space: pre-wrap; word-wrap: break-word; }
"""

MAX_DOC_CHARS = 24000
_MAX_LINE_CHARS = 2000


def _wrap_long_lines(lines: list[str], limit: int = _MAX_LINE_CHARS) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= limit:
            wrapped.append(line)
            continue
        for start in range(0, len(line), limit):
            wrapped.append(line[start : start + limit])
    return wrapped


def _markdown_chunks(markdown: str, max_chars: int = MAX_DOC_CHARS) -> list[str]:
    lines = _wrap_long_lines(markdown.splitlines())
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    in_fence = False

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

    for line in lines:
        add = len(line) + 1
        is_fence_line = line.strip().startswith("```")

        if in_fence:
            if current_len + add > max_chars:
                current.append("```")
                flush()
                current.append("```")
                current_len = 4
            current.append(line)
            current_len += add
            if is_fence_line:
                in_fence = False
            continue

        if current_len + add > max_chars:
            flush()
        current.append(line)
        current_len += add
        if is_fence_line:
            in_fence = True

    flush()
    return chunks


def _chunk_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        heading = _HEADING_RE.match(line.strip())
        if heading is not None:
            text = heading.group(2).strip()
            if text:
                return text
    return fallback


CONTAINER_XML = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


@dataclass(frozen=True)
class BuiltBook:
    path: Path
    title: str


def _inline(text: str) -> str:
    return _BOLD_RE.sub(r"<strong>\1</strong>", _escape(text, quote=False))


def _flush_paragraph(blocks: list[str], paragraph: list[str]) -> None:
    if not paragraph:
        return
    text = " ".join(line.strip() for line in paragraph)
    blocks.append(f"<p>{_inline(text)}</p>")
    paragraph.clear()


def markdown_to_xhtml(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("```"):
            _flush_paragraph(blocks, paragraph)
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            blocks.append(f"<pre><code>{_escape(chr(10).join(code))}</code></pre>")
            continue
        if not stripped:
            _flush_paragraph(blocks, paragraph)
            index += 1
            continue
        heading = _HEADING_RE.match(stripped)
        if heading is not None:
            _flush_paragraph(blocks, paragraph)
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{_inline(heading.group(2).strip())}</h{level}>")
            index += 1
            continue
        quote = _BLOCKQUOTE_RE.match(stripped)
        if quote is not None:
            _flush_paragraph(blocks, paragraph)
            quoted: list[str] = []
            while index < len(lines):
                match = _BLOCKQUOTE_RE.match(lines[index].strip())
                if match is None:
                    break
                quoted.append(match.group(1))
                index += 1
            blocks.append(f"<blockquote><p>{_inline(' '.join(quoted))}</p></blockquote>")
            continue
        paragraph.append(lines[index])
        index += 1
    _flush_paragraph(blocks, paragraph)
    return "\n".join(blocks)


def _content_document(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "  <head>\n"
        f"    <title>{_escape(title)}</title>\n"
        '    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n'
        '    <link rel="stylesheet" type="text/css" href="styles.css"/>\n'
        "  </head>\n"
        "  <body>\n"
        f"{body}\n"
        "  </body>\n"
        "</html>\n"
    )


def _opf(title: str, identifier: str, documents: list[tuple[str, str]]) -> str:
    manifest = [
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="styles" href="styles.css" media-type="text/css"/>',
    ]
    spine: list[str] = []
    for position, (name, _) in enumerate(documents, start=1):
        manifest.append(
            f'<item id="chapter{position}" href="{name}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="chapter{position}"/>')
    manifest_xml = "\n    ".join(manifest)
    spine_xml = "\n    ".join(spine)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"    <dc:title>{_escape(title)}</dc:title>\n"
        f'    <dc:identifier id="bookid">{identifier}</dc:identifier>\n'
        "    <dc:language>en</dc:language>\n"
        "  </metadata>\n"
        "  <manifest>\n"
        f"    {manifest_xml}\n"
        "  </manifest>\n"
        '  <spine toc="ncx">\n'
        f"    {spine_xml}\n"
        "  </spine>\n"
        "</package>\n"
    )


def _ncx(title: str, identifier: str, documents: list[tuple[str, str]]) -> str:
    points: list[str] = []
    for position, (name, document_title) in enumerate(documents, start=1):
        points.append(
            f'    <navPoint id="chapter{position}" playOrder="{position}">'
            f"<navLabel><text>{_escape(document_title)}</text></navLabel>"
            f'<content src="{name}"/></navPoint>'
        )
    points_xml = "\n".join(points)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" '
        '"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        "  <head>\n"
        f'    <meta name="dtb:uid" content="{identifier}"/>\n'
        '    <meta name="dtb:depth" content="1"/>\n'
        '    <meta name="dtb:totalPageCount" content="0"/>\n'
        '    <meta name="dtb:maxPageNumber" content="0"/>\n'
        "  </head>\n"
        f"  <docTitle><text>{_escape(title)}</text></docTitle>\n"
        "  <navMap>\n"
        f"{points_xml}\n"
        "  </navMap>\n"
        "</ncx>\n"
    )


def _conversation_label(conversation: Conversation) -> str:
    return conversation.name or conversation.title


def _default_title(conversations: list[Conversation]) -> str:
    labels = [_conversation_label(conversation) for conversation in conversations]
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]} + {len(labels) - 1} more"


def _write_staging(root: str | Path, title: str, documents: list[tuple[str, str]]) -> None:
    base = Path(root)
    (base / "META-INF").mkdir(parents=True, exist_ok=True)
    (base / "OEBPS").mkdir(parents=True, exist_ok=True)
    (base / "mimetype").write_text(MIMETYPE, encoding="utf-8")
    (base / "META-INF" / "container.xml").write_text(CONTAINER_XML, encoding="utf-8")
    (base / "OEBPS" / "styles.css").write_text(STYLES_CSS, encoding="utf-8")

    manifest: list[tuple[str, str]] = []
    for position, (document_title, markdown) in enumerate(documents, start=1):
        name = f"chapter{position}.xhtml"
        body = markdown_to_xhtml(markdown)
        (base / "OEBPS" / name).write_text(
            _content_document(document_title, body), encoding="utf-8"
        )
        manifest.append((name, document_title))

    identifier = f"urn:uuid:{uuid.uuid4()}"
    (base / "OEBPS" / "content.opf").write_text(
        _opf(title, identifier, manifest), encoding="utf-8"
    )
    (base / "OEBPS" / "toc.ncx").write_text(
        _ncx(title, identifier, manifest), encoding="utf-8"
    )


def _publish(documents: list[tuple[str, str]], book_title: str, out_dir: str | Path) -> BuiltBook:
    destination_dir = Path(out_dir)
    destination = unique_output(destination_dir, f"{sanitize_stem(book_title)}.epub")

    def build(work: str, tmp_name: str) -> None:
        _write_staging(work, book_title, documents)
        repack_epub(work, tmp_name)

    publish_epub(destination, build)
    return BuiltBook(path=destination, title=book_title)


def build_epub(
    conversations: list[Conversation],
    out_dir: str | Path,
    title: str | None = None,
) -> BuiltBook:
    if not conversations:
        raise EpubError("no conversations selected")

    book_title = title.strip() if isinstance(title, str) and title.strip() else _default_title(conversations)
    documents: list[tuple[str, str]] = []
    for conversation in conversations:
        label = _conversation_label(conversation)
        for chunk in _markdown_chunks(render_conversation(conversation)):
            documents.append((_chunk_title(chunk, label), chunk))
    return _publish(documents, book_title, out_dir)


def _title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            heading = stripped[2:].strip()
            if heading:
                return heading
    return "Work Copy"


def build_epub_from_document(
    markdown: str,
    out_dir: str | Path,
    title: str | None = None,
) -> BuiltBook:
    if not isinstance(markdown, str) or not markdown.strip():
        raise EpubError("work copy is empty")

    book_title = title.strip() if isinstance(title, str) and title.strip() else _title_from_markdown(markdown)
    documents = [(_chunk_title(chunk, book_title), chunk) for chunk in _markdown_chunks(markdown)]
    return _publish(documents, book_title, out_dir)
