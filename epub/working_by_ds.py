import os
import re
import shutil
import zipfile
import tempfile
from lxml import etree


# ============================================================
# 电纸书兼容策略（定稿 v6）
# ------------------------------------------------------------
# 实测结论：
#   - font-weight: bold             ✅ 有效
#   - font-style: italic            ❌ 无效
#   - text-decoration: line-through ❌ 无效
#   - <hr>                          ❌ 不渲染
#
# 因此：
# 1) <hr>                  -> 纯文本 "---"
# 2) <em>/<i>              -> 纯文本 *…*（支持内嵌子元素，星号放首尾）
# 3) CSS 里带 font-style: italic 的 class（如 .calibre9）
#                          -> 命中该 class 的元素也加 *…*
# 4) <strong>/<b>          -> 保留标签 + 内联 font-weight: bold
# 5) <strike>/<s>/<del>    -> 纯文本 ~~…~~
# 6) <head> 注入兜底 <style>
# 7) CSS 里 .toc-heading 规则整体替换为统一版本
# ============================================================

ITALIC_MARK = '*'
STRIKE_MARK = '~~'

INLINE_STYLE = {
    'strong': 'font-weight: bold;',
    'b':      'font-weight: bold;',
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


# ------------------------------------------------------------
# 工具
# ------------------------------------------------------------

def unpack_epub(epub_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(epub_path, 'r') as z:
        z.extractall(out_dir)
    print(f"[unpack] {epub_path} -> {out_dir}")
    return out_dir


def _localname(tag):
    if not isinstance(tag, str):
        return None
    return etree.QName(tag).localname if '}' in tag else tag


def _ensure_style_in_head(tree, css_text):
    root = tree.getroot()
    head = None
    for el in root.iter():
        if _localname(el.tag) == 'head':
            head = el
            break
    if head is None:
        return False

    for st in head.iter():
        if _localname(st.tag) == 'style' and st.get('data-injected') == 'ebook-fallback':
            st.text = css_text
            return True

    ns = etree.QName(head.tag).namespace if isinstance(head.tag, str) and '}' in head.tag else None
    if ns:
        st = etree.SubElement(head, f'{{{ns}}}style')
    else:
        st = etree.SubElement(head, 'style')

    st.set('type', 'text/css')
    st.set('data-injected', 'ebook-fallback')
    st.text = css_text
    return True


def _handle_hr(tree):
    changed = False
    for elem in reversed(list(tree.iter())):
        if _localname(elem.tag) != 'hr':
            continue
        parent = elem.getparent()
        if parent is None:
            continue

        prev = elem.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or '').rstrip('\n') + '\n'
        elif parent.text is not None:
            parent.text = parent.text.rstrip('\n') + '\n'

        tail_text = (elem.tail or '')
        elem.tail = '\n---\n' + tail_text
        parent.remove(elem)

        if prev is not None:
            prev.tail = (prev.tail or '').rstrip('\n') + '\n---\n'
        else:
            parent.text = (parent.text or '').rstrip('\n') + '\n---\n'

        changed = True
    return changed


# ------------------------------------------------------------
# 核心：给元素加前后缀标记，支持内嵌子元素
# ------------------------------------------------------------

def _wrap_with_mark(elem, mark, marked_attr, changed):
    """给 elem 加 mark 前后缀。

    策略：
      - 无子元素：elem.text = mark + text + mark
      - 有子元素：前缀加到 elem.text（或第一个子节点 text 的开头）
                  后缀加到最后一个子节点的 tail 末尾
      用 marked_attr="1" 保证幂等。
    """
    if not mark:
        return changed
    if elem.get(marked_attr) == '1':
        return changed

    # ---- 情况 1：纯文本元素 ----
    if len(elem) == 0:
        full = elem.text or ''
        if not full:
            return changed
        elem.text = f"{mark}{full}{mark}"
        elem.set(marked_attr, '1')
        return True

    # ---- 情况 2：有子元素 ----
    # 前缀：优先放到 elem.text 开头；否则放到第一个子元素的 text 开头
    if elem.text is not None and elem.text != '':
        elem.text = f"{mark}{elem.text}"
    else:
        first = elem[0]
        # 找第一个有文本的位置：first.text 或它的后代
        node = first
        while node is not None and (node.text is None or node.text == ''):
            if len(node) == 0:
                node = None
                break
            node = node[0]
        if node is not None and node.text:
            node.text = f"{mark}{node.text}"

    # 后缀：放到最后一个子元素的 tail 末尾；如果没有 tail，放到它最后一个后代的 tail
    last = elem[-1]
    node = last
    # 找最后一个有文本的位置
    target = None
    while node is not None:
        if node.tail is not None and node.tail != '':
            target = node
            break
        if len(node) > 0:
            node = node[-1]
        else:
            target = node
            break
    if target is not None:
        target.tail = (target.tail or '') + mark
    # 如果实在没有 tail 位置，退化为在最后子元素后加一个 tail
    elif elem[-1].tail is None:
        elem[-1].tail = mark

    elem.set(marked_attr, '1')
    return True


def _handle_italic_star(elem, changed):
    return _wrap_with_mark(elem, ITALIC_MARK, 'data-em-marked', changed)


def _handle_strike_mark(elem, changed):
    return _wrap_with_mark(elem, STRIKE_MARK, 'data-strike-marked', changed)


# ------------------------------------------------------------
# CSS 分析
# ------------------------------------------------------------

_CSS_RULE_RE = re.compile(r'([^{}]*?)\{([^{}]*)\}', re.DOTALL)
_FONT_STYLE_ITALIC_RE = re.compile(r'font-style\s*:\s*[^;{}]*italic', re.IGNORECASE)
_CLASS_SELECTOR_RE = re.compile(r'\.([A-Za-z_][\w-]*)')


def _extract_italic_classes(css_text):
    classes = set()
    for m in _CSS_RULE_RE.finditer(css_text):
        if not _FONT_STYLE_ITALIC_RE.search(m.group(2)):
            continue
        classes |= set(_CLASS_SELECTOR_RE.findall(m.group(1)))
    return classes


def _scan_css_for_italic_classes(src_dir):
    all_classes = set()

    for root, _, files in os.walk(src_dir):
        for fname in files:
            full = os.path.join(root, fname)
            low = fname.lower()

            if low.endswith('.css'):
                try:
                    with open(full, 'r', encoding='utf-8') as f:
                        css = f.read()
                except UnicodeDecodeError:
                    with open(full, 'r', encoding='latin-1') as f:
                        css = f.read()
                except Exception as e:
                    print(f"[css skip] {full}: {e}")
                    continue
                all_classes |= _extract_italic_classes(css)

            elif low.endswith(('.xhtml', '.html', '.htm')):
                try:
                    parser = etree.XMLParser(recover=True, encoding='utf-8')
                    tree = etree.parse(full, parser)
                except Exception:
                    continue
                for el in tree.iter():
                    if _localname(el.tag) == 'style' and el.text:
                        all_classes |= _extract_italic_classes(el.text)

    if all_classes:
        print(f"[css italic] 发现 {len(all_classes)} 个 italic 类：{sorted(all_classes)}")
    else:
        print("[css italic] 未发现任何 italic 类")
    return all_classes


# ------------------------------------------------------------
# CSS：替换 .toc-heading
# ------------------------------------------------------------

def _replace_toc_heading_in_css(css_text):
    changed = False

    def repl(match):
        nonlocal changed
        selectors = match.group(1)
        if re.search(r'(?<![\w-])\.toc-heading(?![\w-])', selectors):
            changed = True
            return TOC_HEADING_CSS
        return match.group(0)

    return _CSS_RULE_RE.sub(repl, css_text), changed


def _patch_css_files(src_dir):
    count = 0
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.lower().endswith('.css'):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    css = f.read()
            except UnicodeDecodeError:
                with open(path, 'r', encoding='latin-1') as f:
                    css = f.read()
            except Exception as e:
                print(f"[css skip] {path}: {e}")
                continue

            new_css, changed = _replace_toc_heading_in_css(css)
            if changed:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_css)
                count += 1
                print(f"[css patch] {path}")

    print(f"[css patch] 共修改 {count} 个 CSS 文件")
    return count


# ------------------------------------------------------------
# XHTML 处理
# ------------------------------------------------------------

def _handle_inline_styles(tree, italic_classes):
    changed = False
    for elem in reversed(list(tree.iter())):
        local = _localname(elem.tag)
        if local is None:
            continue

        # 1) <em>/<i>
        if local in ('em', 'i'):
            changed = _handle_italic_star(elem, changed)
            continue

        # 2) <strike>/<s>/<del>
        if local in ('strike', 's', 'del'):
            changed = _handle_strike_mark(elem, changed)
            continue

        # 3) class 命中 italic
        class_attr = elem.get('class') or ''
        if class_attr and italic_classes:
            if any(c in italic_classes for c in class_attr.split()):
                changed = _handle_italic_star(elem, changed)

        # 4) 粗体
        style = INLINE_STYLE.get(local)
        if style:
            old = elem.get('style') or ''
            if style not in old:
                elem.set('style', (old + '; ' if old else '') + style)
                changed = True

    return changed


# ------------------------------------------------------------
# 主转换
# ------------------------------------------------------------

def convert_styles(src_dir, debug=False):
    italic_classes = _scan_css_for_italic_classes(src_dir)

    count = 0
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.lower().endswith(('.xhtml', '.html', '.htm')):
                continue

            path = os.path.join(root, fname)
            try:
                parser = etree.XMLParser(recover=True, encoding='utf-8')
                tree = etree.parse(path, parser)
            except Exception as e:
                print(f"[skip] {path}: {e}")
                continue

            changed = False
            changed |= _handle_hr(tree)
            changed |= _handle_inline_styles(tree, italic_classes)
            changed |= _ensure_style_in_head(tree, FALLBACK_CSS)

            if changed:
                tree.write(path, encoding='utf-8', xml_declaration=True)
                count += 1
                print(f"[convert] {path}")

    print(f"[convert] 共修改 {count} 个 XHTML 文件")
    _patch_css_files(src_dir)
    return count


# ------------------------------------------------------------
# 重新打包
# ------------------------------------------------------------

def repack_epub(src_dir, out_path):
    if os.path.exists(out_path):
        os.remove(out_path)

    with zipfile.ZipFile(out_path, 'w') as z:
        mimetype_path = os.path.join(src_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            z.write(mimetype_path, 'mimetype',
                    compress_type=zipfile.ZIP_STORED)
        else:
            z.writestr('mimetype', 'application/epub+zip',
                       compress_type=zipfile.ZIP_STORED)
            print("[warn] 原文件缺少 mimetype，已补写")

        for root, _, files in os.walk(src_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, src_dir).replace(os.sep, '/')
                if rel == 'mimetype':
                    continue
                z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED)

    print(f"[repack] -> {out_path}")


# ------------------------------------------------------------
# 批量处理
# ------------------------------------------------------------

def process_folder(folder_path, out_folder=None, recursive=True):
    if out_folder is None:
        out_folder = folder_path.rstrip('/\\') + '_converted'
    os.makedirs(out_folder, exist_ok=True)

    epub_files = []
    if recursive:
        for root, _, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith('.epub'):
                    epub_files.append(os.path.join(root, f))
    else:
        for f in os.listdir(folder_path):
            full = os.path.join(folder_path, f)
            if os.path.isfile(full) and f.lower().endswith('.epub'):
                epub_files.append(full)

    print(f"[scan] 找到 {len(epub_files)} 个 EPUB")

    success, failed = 0, []
    for i, epub_in in enumerate(epub_files, 1):
        rel = os.path.relpath(epub_in, folder_path)
        epub_out = os.path.join(out_folder, rel)
        os.makedirs(os.path.dirname(epub_out), exist_ok=True)

        print(f"\n[{i}/{len(epub_files)}] {rel}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                unpack_epub(epub_in, tmp)
                convert_styles(tmp)
                repack_epub(tmp, epub_out)
            success += 1
        except Exception as e:
            print(f"[fail] {rel}: {e}")
            failed.append((rel, str(e)))

    print(f"\n[done] 成功 {success}，失败 {len(failed)}")
    for name, err in failed:
        print(f"  - {name}: {err}")

    return success, failed


if __name__ == '__main__':
    process_folder('./books',
                   out_folder='D:/',
                   recursive=True)

    if os.path.exists('D:/bak'):
        shutil.rmtree('D:/bak')
    shutil.copytree('./books', 'D:/bak/books')
    print("[backup] ./books -> D:/bak/books")
