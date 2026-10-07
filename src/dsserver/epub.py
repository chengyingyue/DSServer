from __future__ import annotations

import os
import re
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

from .naming import unique_name

ITALIC_MARK = "*"
STRIKE_MARK = "~~"

INLINE_STYLE = {
    "strong": "font-weight: bold;",
    "b": "font-weight: bold;",
}

FALLBACK_CSS = """
hr { border: none; border-top: 1px solid #000; margin: 1em 0; }
strong, b, .bold { font-weight: bold; }
.calibre5 { display: block; margin: 0 0 0 1em; }
.calibre6 { display: block; font-size: 1.41667em; font-weight: bold;
            line-height: 1.2; text-align: center; margin: 0.67em 0; }
"""

TOC_HEADING_CSS = """\
.toc-heading {
  display: block;
  margin: 1em 0;
}
"""


class EpubError(Exception):
    """Raised when an input cannot be converted into an e-reader EPUB."""


def unpack_epub(epub_path: str | Path, out_dir: str | Path) -> str:
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(epub_path, "r") as archive:
        archive.extractall(out_dir)
    return str(out_dir)


def _localname(tag: Any) -> str | None:
    if not isinstance(tag, str):
        return None
    return etree.QName(tag).localname if "}" in tag else tag


def _ensure_style_in_head(tree: Any, css_text: str) -> bool:
    root = tree.getroot()
    head = None
    for el in root.iter():
        if _localname(el.tag) == "head":
            head = el
            break
    if head is None:
        return False

    for st in head.iter():
        if _localname(st.tag) == "style" and st.get("data-injected") == "ebook-fallback":
            st.text = css_text
            return True

    ns = etree.QName(head.tag).namespace if isinstance(head.tag, str) and "}" in head.tag else None
    if ns:
        st = etree.SubElement(head, f"{{{ns}}}style")
    else:
        st = etree.SubElement(head, "style")

    st.set("type", "text/css")
    st.set("data-injected", "ebook-fallback")
    st.text = css_text
    return True


def _handle_hr(tree: Any) -> bool:
    changed = False
    for elem in reversed(list(tree.iter())):
        if _localname(elem.tag) != "hr":
            continue
        parent = elem.getparent()
        if parent is None:
            continue

        prev = elem.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "").rstrip("\n") + "\n"
        elif parent.text is not None:
            parent.text = parent.text.rstrip("\n") + "\n"

        tail_text = elem.tail or ""
        elem.tail = "\n---\n" + tail_text
        parent.remove(elem)

        if prev is not None:
            prev.tail = (prev.tail or "").rstrip("\n") + "\n---\n"
        else:
            parent.text = (parent.text or "").rstrip("\n") + "\n---\n"

        changed = True
    return changed


def _wrap_with_mark(elem: Any, mark: str, marked_attr: str, changed: bool) -> bool:
    if not mark:
        return changed
    if elem.get(marked_attr) == "1":
        return changed

    if len(elem) == 0:
        full = elem.text or ""
        if not full:
            return changed
        elem.text = f"{mark}{full}{mark}"
        elem.set(marked_attr, "1")
        return True

    if elem.text is not None and elem.text != "":
        elem.text = f"{mark}{elem.text}"
    else:
        first = elem[0]
        node: Any = first
        while node is not None and (node.text is None or node.text == ""):
            if len(node) == 0:
                node = None
                break
            node = node[0]
        if node is not None and node.text:
            node.text = f"{mark}{node.text}"

    last = elem[-1]
    node = last
    target = None
    while node is not None:
        if node.tail is not None and node.tail != "":
            target = node
            break
        if len(node) > 0:
            node = node[-1]
        else:
            target = node
            break
    if target is not None:
        target.tail = (target.tail or "") + mark
    elif elem[-1].tail is None:
        elem[-1].tail = mark

    elem.set(marked_attr, "1")
    return True


def _handle_italic_star(elem: Any, changed: bool) -> bool:
    return _wrap_with_mark(elem, ITALIC_MARK, "data-em-marked", changed)


def _handle_strike_mark(elem: Any, changed: bool) -> bool:
    return _wrap_with_mark(elem, STRIKE_MARK, "data-strike-marked", changed)


_CSS_RULE_RE = re.compile(r"([^{}]*?)\{([^{}]*)\}", re.DOTALL)
_FONT_STYLE_ITALIC_RE = re.compile(r"font-style\s*:\s*[^;{}]*italic", re.IGNORECASE)
_CLASS_SELECTOR_RE = re.compile(r"\.([A-Za-z_][\w-]*)")


def _extract_italic_classes(css_text: str) -> set[str]:
    classes: set[str] = set()
    for m in _CSS_RULE_RE.finditer(css_text):
        if not _FONT_STYLE_ITALIC_RE.search(m.group(2)):
            continue
        classes |= set(_CLASS_SELECTOR_RE.findall(m.group(1)))
    return classes


def _scan_css_for_italic_classes(src_dir: str | Path) -> set[str]:
    all_classes: set[str] = set()

    for root, _, files in os.walk(src_dir):
        for fname in files:
            full = os.path.join(root, fname)
            low = fname.lower()

            if low.endswith(".css"):
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        css = f.read()
                except UnicodeDecodeError:
                    with open(full, "r", encoding="latin-1") as f:
                        css = f.read()
                except OSError:
                    continue
                all_classes |= _extract_italic_classes(css)

            elif low.endswith((".xhtml", ".html", ".htm")):
                try:
                    parser = etree.XMLParser(recover=True, encoding="utf-8")
                    tree = etree.parse(full, parser)
                except Exception:
                    continue
                for el in tree.iter():
                    if _localname(el.tag) == "style" and el.text:
                        all_classes |= _extract_italic_classes(el.text)

    return all_classes


def _replace_toc_heading_in_css(css_text: str) -> tuple[str, bool]:
    changed = False

    def repl(match: Any) -> str:
        nonlocal changed
        selectors = match.group(1)
        if re.search(r"(?<![\w-])\.toc-heading(?![\w-])", selectors):
            changed = True
            return TOC_HEADING_CSS
        return str(match.group(0))

    return _CSS_RULE_RE.sub(repl, css_text), changed


def _patch_css_files(src_dir: str | Path) -> int:
    count = 0
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.lower().endswith(".css"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    css = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="latin-1") as f:
                    css = f.read()
            except OSError:
                continue

            new_css, changed = _replace_toc_heading_in_css(css)
            if changed:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_css)
                count += 1

    return count


def _handle_inline_styles(tree: Any, italic_classes: set[str]) -> bool:
    changed = False
    for elem in reversed(list(tree.iter())):
        local = _localname(elem.tag)
        if local is None:
            continue

        if local in ("em", "i"):
            changed = _handle_italic_star(elem, changed)
            continue

        if local in ("strike", "s", "del"):
            changed = _handle_strike_mark(elem, changed)
            continue

        class_attr = elem.get("class") or ""
        if class_attr and italic_classes:
            if any(c in italic_classes for c in class_attr.split()):
                changed = _handle_italic_star(elem, changed)

        style = INLINE_STYLE.get(local)
        if style:
            old = elem.get("style") or ""
            if style not in old:
                elem.set("style", (old + "; " if old else "") + style)
                changed = True

    return changed


def convert_styles(src_dir: str | Path, debug: bool = False) -> int:
    italic_classes = _scan_css_for_italic_classes(src_dir)

    count = 0
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.lower().endswith((".xhtml", ".html", ".htm")):
                continue

            path = os.path.join(root, fname)
            try:
                parser = etree.XMLParser(recover=True, encoding="utf-8")
                tree = etree.parse(path, parser)
            except Exception:
                continue

            changed = False
            changed |= _handle_hr(tree)
            changed |= _handle_inline_styles(tree, italic_classes)
            changed |= _ensure_style_in_head(tree, FALLBACK_CSS)

            if changed:
                tree.write(path, encoding="utf-8", xml_declaration=True)
                count += 1

    _patch_css_files(src_dir)
    return count


def repack_epub(src_dir: str | Path, out_path: str | Path) -> None:
    if os.path.exists(out_path):
        os.remove(out_path)

    with zipfile.ZipFile(out_path, "w") as archive:
        mimetype_path = os.path.join(src_dir, "mimetype")
        if os.path.exists(mimetype_path):
            archive.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        else:
            archive.writestr(
                "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
            )

        for root, _, files in os.walk(src_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, src_dir).replace(os.sep, "/")
                if rel == "mimetype":
                    continue
                archive.write(full, rel, compress_type=zipfile.ZIP_DEFLATED)


def list_epubs(directory: str | Path) -> list[str]:
    path = Path(directory)
    if not path.is_dir():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".epub")


def unique_output(out_dir: Path, name: str) -> Path:
    return out_dir / unique_name(name, lambda candidate: (out_dir / candidate).exists())


def publish_epub(destination: Path, build: Callable[[str, str], None]) -> Path:
    destination_dir = destination.parent
    destination_dir.mkdir(parents=True, exist_ok=True)

    handle, tmp_name = tempfile.mkstemp(suffix=".epub", dir=destination_dir)
    os.close(handle)
    try:
        with tempfile.TemporaryDirectory() as work:
            build(work, tmp_name)
        os.replace(tmp_name, destination)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise

    return destination


def convert_epub(src: str | Path, out_dir: str | Path) -> Path:
    source = Path(src)
    if not source.is_file():
        raise EpubError(f"file not found: {source.name}")

    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        raise EpubError(f"{source.name} is not a valid EPUB (not a zip archive)")

    if "META-INF/container.xml" not in names:
        raise EpubError(f"{source.name} is not a valid EPUB (missing META-INF/container.xml)")

    destination_dir = Path(out_dir)
    destination = unique_output(destination_dir, source.name)

    def build(work: str, tmp_name: str) -> None:
        unpack_epub(str(source), work)
        convert_styles(work)
        repack_epub(work, tmp_name)

    return publish_epub(destination, build)
