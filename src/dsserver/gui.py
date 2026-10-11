from __future__ import annotations

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DSServer</title>
<style>
  :root {
    --border: #e3e6ea; --muted: #6b7280; --accent: #2563eb; --accent-soft: #eff4ff;
    --bg: #f6f7f9; --card: #ffffff; --text: #1f2933; --danger: #dc2626; --danger-soft: #fef2f2;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 1.5rem 1rem 3rem; background: var(--bg); color: var(--text);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 66rem; margin: 0 auto; }
  .page { display: flex; align-items: baseline; gap: 0.6rem; margin: 0 0 1rem; }
  .page h1 { font-size: 1.15rem; margin: 0; }
  .page .tag { font-size: 0.72rem; color: var(--muted); }
  .section {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    margin-bottom: 0.9rem; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04); overflow: hidden;
  }
  .section > summary {
    list-style: none; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;
    padding: 0.7rem 1rem; font-weight: 600; user-select: none;
  }
  .section > summary::-webkit-details-marker { display: none; }
  .section[open] > summary { border-bottom: 1px solid var(--border); }
  .body { padding: 0.85rem 1rem; }
  .chev { transition: transform 0.15s ease; color: var(--muted); }
  .section[open] > summary > .chev { transform: rotate(90deg); }
  .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.7rem; }
  .toolbar:last-child { margin-bottom: 0; }
  .grow { flex: 1 1 12rem; }
  .muted { color: var(--muted); }
  .count { color: var(--muted); font-weight: 400; font-size: 0.82rem; }

  input[type=text], input[type=file] {
    padding: 0.38rem 0.55rem; border: 1px solid var(--border); border-radius: 8px;
    background: #fff; color: var(--text); font: inherit; max-width: 100%;
  }
  input[type=text]:focus { outline: 2px solid var(--accent-soft); border-color: var(--accent); }
  input[type=checkbox] { width: 1rem; height: 1rem; cursor: pointer; }
  select { padding: 0.38rem 0.55rem; border: 1px solid var(--border); border-radius: 8px; font: inherit; }

  .btn {
    display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.38rem 0.7rem;
    border: 1px solid var(--border); border-radius: 8px; background: #fff; color: var(--text);
    font: inherit; cursor: pointer; white-space: nowrap;
  }
  .btn:hover { background: #f3f5f8; }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn.primary:hover { background: #1d4ed8; }

  .icon-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 1.75rem; height: 1.75rem; padding: 0;
    border: 1px solid var(--border); border-radius: 7px;
    background: #fff; color: #5b6472; cursor: pointer; flex: none;
  }
  .icon-btn:hover { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); }
  .icon-btn.danger:hover { background: var(--danger-soft); color: var(--danger); border-color: var(--danger); }
  .icon { width: 1rem; height: 1rem; display: block; flex: none; }

  .tree-panel { border: 1px solid var(--border); border-radius: 10px; padding: 0.4rem 0.5rem; background: #fcfdfe; }
  ul.tree { list-style: none; padding-left: 1.1rem; margin: 0; }
  ul.tree.root { padding-left: 0; }
  ul.tree details > summary { list-style: none; cursor: pointer; }
  ul.tree summary::-webkit-details-marker { display: none; }
  .node-row { display: flex; align-items: center; gap: 0.4rem; padding: 0.15rem 0.35rem; border-radius: 7px; min-height: 1.75rem; }
  .node-row:hover { background: #f1f4f8; }
  .node-row .name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .node-row.dir .name { font-weight: 600; }
  .node-row .actions { display: flex; gap: 0.1rem; flex: none; }
  ul.tree details[open] > summary .chev { transform: rotate(90deg); }
  .node-icon { color: var(--muted); }
  .node-row.dir > .node-icon { color: #d99a2b; }
  .conv-meta { color: var(--muted); font-size: 0.8rem; flex: none; }
  li[hidden] { display: none; }
  .node-row.drop { background: var(--accent-soft); box-shadow: inset 0 0 0 1px var(--accent); }
  ul.tree.root > li { margin: 0.1rem 0; }
  .root-label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }

  #viewer { max-width: 48rem; width: 90%; border: 1px solid var(--border); border-radius: 12px; }
  #viewer-body { max-height: 70vh; overflow: auto; }
  #viewer-body pre { white-space: pre-wrap; word-break: break-word; background: #f6f8fa; padding: 0.75rem; border-radius: 8px; }
  #folder-picker { border: 1px solid var(--border); border-radius: 12px; min-width: 20rem; }
  #folder-picker-select { width: 100%; }
  #work-content { width: 100%; padding: 0.6rem; border: 1px solid var(--border); border-radius: 10px; font: 13px/1.5 ui-monospace, Consolas, monospace; }
  #work-outline { margin-bottom: 0.5rem; }
  #work-outline ul { margin: 0.2rem 0; padding-left: 1.2rem; }
  #work-list { display: flex; flex-wrap: wrap; gap: 0.3rem; }
</style>
</head>
<body>
<div class="wrap">
<div class="page"><h1>DSServer</h1><span class="tag">local bridge &middot; gui v8</span></div>

<details class="section" id="section-epub" open>
  <summary><svg class="icon chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg><span>EPUB</span></summary>
  <div class="body">
    <div class="toolbar">
      <input id="build-title" class="grow" type="text" placeholder="Book title (optional)">
      <button class="btn primary" id="build"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 0-2 2z"/><path d="M19 17H6"/></svg><span>Build EPUB</span></button>
      <span class="muted" id="build-status"></span>
    </div>
    <div class="toolbar">
      <button class="btn" id="scan"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg><span>Scan inbox</span></button>
      <input id="epub-upload" type="file" accept=".epub">
      <input id="upload-dir" class="grow" type="text" placeholder="target folder (optional, e.g. inbox/ao3)">
      <button class="btn" id="upload"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21V9"/><path d="M7 14l5-5 5 5"/><path d="M5 3h14"/></svg><span>Upload</span></button>
      <span class="muted" id="upload-status"></span>
    </div>
    <div class="tree-panel"><div id="epub-tree"></div></div>
    <p class="muted" id="epub-status"></p>
  </div>
</details>

<details class="section" id="section-conversations" open>
  <summary><svg class="icon chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg><span>Conversations</span><span class="count" id="conv-count"></span></summary>
  <div class="body">
    <div class="toolbar">
      <input id="filter" class="grow" type="text" placeholder="Filter by name">
      <button class="btn" id="conv-new-folder"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 11v6M9 14h6"/></svg><span>New folder</span></button>
      <button class="btn" id="conv-move-selected"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M13 9h6M16 6l3 3-3 3"/></svg><span>Move selected</span></button>
      <label class="muted"><input type="checkbox" id="select-all"> Select all</label>
      <span class="muted" id="conv-selected"></span>
    </div>
    <div class="tree-panel"><div id="conv-tree"></div></div>
    <p class="muted" id="conv-status"></p>
  </div>
</details>

<details class="section" id="section-work" open>
  <summary><svg class="icon chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg><span>Work copy</span></summary>
  <div class="body">
    <p class="muted">Create an editable, named copy of the ticked Conversations, refine it by chapter, build an EPUB from it, then discard it. Editing never changes the original Conversations or the log.</p>
    <div class="toolbar">
      <input id="work-name" class="grow" type="text" placeholder="Work copy name (optional)">
      <button class="btn primary" id="work-create"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 0-2 2z"/><path d="M19 17H6"/></svg><span>Create from selection</span></button>
      <span class="muted" id="work-status"></span>
    </div>
    <div class="toolbar">
      <span class="muted">Work copies</span>
      <button class="icon-btn" id="work-refresh" title="Refresh"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg></button>
      <span class="count" id="work-list"></span>
    </div>
    <div class="toolbar">
      <button class="btn" id="work-rename"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg><span>Rename</span></button>
      <button class="btn" id="work-save"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h7V3"/><path d="M8 15h8v6H8z"/></svg><span>Save</span></button>
      <button class="btn" id="work-download"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/></svg><span>Download MD</span></button>
      <button class="btn" id="work-build"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 0-2 2z"/><path d="M19 17H6"/></svg><span>Build EPUB</span></button>
      <button class="btn" id="work-discard"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/></svg><span>Discard</span></button>
    </div>
    <p class="muted">Chapters split automatically at every <code>#</code> heading. To force a break without a heading, type a line containing just <code>&lt;!-- chapter --&gt;</code>.</p>
    <div id="work-outline"></div>
    <textarea id="work-content" rows="16"></textarea>
    <input id="work-id" type="hidden">
  </div>
</details>
</div>

<dialog id="viewer">
  <div class="toolbar" style="justify-content: flex-end;">
    <button class="icon-btn" id="viewer-close" title="Close"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
  </div>
  <h2 id="viewer-title"></h2>
  <div id="viewer-body"></div>
</dialog>

<dialog id="folder-picker">
  <h3>Move selected to folder</h3>
  <select id="folder-picker-select"></select>
  <div class="toolbar" style="justify-content: flex-end; margin-top: 0.7rem;">
    <button class="btn" id="folder-picker-cancel">Cancel</button>
    <button class="btn primary" id="folder-picker-ok">Move</button>
  </div>
</dialog>

<dialog id="render-picker">
  <h3 id="render-picker-title">Rendering</h3>
  <label class="muted" style="display:block; margin:0.4rem 0;"><input type="radio" name="render-mode" value="normal"> Normal &mdash; code blocks render as code</label>
  <label class="muted" style="display:block; margin:0.4rem 0;"><input type="radio" name="render-mode" value="plain_code"> Ignore ``` fences &mdash; code content renders as normal markdown</label>
  <div class="toolbar" style="justify-content: flex-end; margin-top: 0.7rem;">
    <button class="btn" id="render-picker-cancel">Cancel</button>
    <button class="btn primary" id="render-picker-ok">Save</button>
  </div>
</dialog>
<script>
const NS = "http://www.w3.org/2000/svg";

const ICON_PATHS = {
  chevron: '<path d="M9 6l6 6-6 6"/>',
  eye: '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  pencil: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  'folder-plus': '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 11v6M9 14h6"/>',
  file: '<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v4h4"/>',
  download: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
  convert: '<path d="M4 12a8 8 0 0 1 13-6l3 3"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-13 6l-3-3"/><path d="M4 20v-5h5"/>',
  move: '<path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M13 9h6M16 6l3 3-3 3"/>',
  scan: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  upload: '<path d="M12 21V9"/><path d="M7 14l5-5 5 5"/><path d="M5 3h14"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 0-2 2z"/><path d="M19 17H6"/>',
  save: '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h7V3"/><path d="M8 15h8v6H8z"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  break: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/>',
  type: '<path d="M4 7V5h16v2"/><path d="M9 19h6"/><path d="M12 5v14"/>',
};
function icon(name, extra) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "icon" + (extra ? " " + extra : ""));
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.innerHTML = ICON_PATHS[name] || "";
  return svg;
}

function iconButton(name, title, handler, danger) {
  const button = document.createElement("button");
  button.className = "icon-btn" + (danger ? " danger" : "");
  button.title = title;
  button.setAttribute("aria-label", title);
  button.appendChild(icon(name));
  button.addEventListener("click", handler);
  return button;
}

let conversations = [];
let folders = [];

function folderMap() {
  const map = new Map();
  for (const folder of folders) map.set(folder.id, folder);
  return map;
}

function folderPath(id) {
  const map = folderMap();
  const parts = [];
  let current = id;
  let guard = 0;
  while (current && map.has(current) && guard < 100) {
    parts.unshift(map.get(current).name);
    current = map.get(current).parent;
    guard += 1;
  }
  return parts.join('/');
}

function resolveFolderPath(path) {
  const trimmed = (path || '').trim().replace(/^\\/+|\\/+$/g, '');
  if (!trimmed) return '';
  const target = folders.find(
    (folder) => folderPath(folder.id).toLowerCase() === trimmed.toLowerCase(),
  );
  return target ? target.id : null;
}

function folderChildren(parent) {
  return folders.filter((folder) => folder.parent === parent);
}

function conversationsIn(folderId) {
  return conversations.filter((conversation) => (conversation.folder || '') === folderId);
}

function setConvStatus(message) {
  document.getElementById('conv-status').textContent = message;
}

async function loadConversations() {
  const [convResponse, folderResponse] = await Promise.all([
    fetch('/api/conversations'),
    fetch('/api/folders'),
  ]);
  conversations = await convResponse.json();
  const folderBody = await folderResponse.json();
  folders = folderBody.folders || [];
  renderConversations();
}

function renderConversations() {
  const container = document.getElementById('conv-tree');
  container.replaceChildren();
  const root = document.createElement('ul');
  root.className = 'tree root';
  root.appendChild(renderUnfiled());
  for (const folder of folderChildren('')) {
    root.appendChild(renderFolder(folder));
  }
  container.appendChild(root);
  document.getElementById('conv-count').textContent = conversations.length + ' total';
  applyFilter();
}

function renderUnfiled() {
  const li = document.createElement('li');
  li.className = 'folder-node';
  const label = document.createElement('div');
  label.className = 'node-row root-label';
  const name = document.createElement('span');
  name.className = 'name';
  name.textContent = 'Unfiled';
  label.appendChild(name);
  makeDropTarget(label, '');
  li.appendChild(label);
  const ul = document.createElement('ul');
  ul.className = 'tree';
  for (const conversation of conversationsIn('')) {
    ul.appendChild(renderConversation(conversation));
  }
  li.appendChild(ul);
  return li;
}

function renderFolder(folder) {
  const li = document.createElement('li');
  li.className = 'folder-node';
  const details = document.createElement('details');
  details.open = true;
  const summary = document.createElement('summary');
  summary.className = 'node-row dir';

  const chev = icon('chevron', 'chev');
  summary.appendChild(chev);
  const folderIcon = icon('folder', 'node-icon');
  summary.appendChild(folderIcon);

  const name = document.createElement('span');
  name.className = 'name';
  name.textContent = folder.name;
  name.title = folderPath(folder.id);
  summary.appendChild(name);

  const count = document.createElement('span');
  count.className = 'count';
  count.textContent = String(conversationsIn(folder.id).length);
  summary.appendChild(count);

  const actions = document.createElement('span');
  actions.className = 'actions';
  actions.appendChild(iconButton('folder-plus', 'New subfolder', () => createFolder(folder.id)));
  actions.appendChild(iconButton('type', renderLabel(folder.render), () => chooseRender(folder)));
  actions.appendChild(iconButton('pencil', 'Rename folder', () => renameFolder(folder)));
  actions.appendChild(iconButton('trash', 'Delete folder', () => deleteFolder(folder), true));
  summary.appendChild(actions);

  makeDropTarget(summary, folder.id);
  details.appendChild(summary);

  const ul = document.createElement('ul');
  ul.className = 'tree';
  for (const conversation of conversationsIn(folder.id)) {
    ul.appendChild(renderConversation(conversation));
  }
  for (const child of folderChildren(folder.id)) {
    ul.appendChild(renderFolder(child));
  }
  details.appendChild(ul);
  li.appendChild(details);
  return li;
}

function renderConversation(conversation) {
  const li = document.createElement('li');
  li.className = 'conv-row';
  li.draggable = true;
  const row = document.createElement('span');
  row.className = 'node-row';

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className = 'conv-check';
  checkbox.dataset.key = conversation.key;
  checkbox.dataset.branch = String(conversation.branch);
  checkbox.addEventListener('change', updateSelectedCount);
  row.appendChild(checkbox);

  const link = document.createElement('a');
  link.className = 'name';
  link.textContent = conversation.name;
  link.title = conversation.name;
  link.addEventListener('click', () => view(conversation));
  row.appendChild(link);

  const meta = document.createElement('span');
  meta.className = 'conv-meta';
  meta.textContent = conversation.date + ' \\u00b7 ' + conversation.turns;
  row.appendChild(meta);

  const actions = document.createElement('span');
  actions.className = 'actions';
  actions.appendChild(iconButton('eye', 'View', () => view(conversation)));
  actions.appendChild(iconButton('move', 'Move to folder', () => moveConversation(conversation)));
  actions.appendChild(iconButton('pencil', 'Rename', () => rename(conversation)));
  actions.appendChild(iconButton('trash', 'Delete', () => removeConversation(conversation), true));
  row.appendChild(actions);

  li.appendChild(row);
  li.addEventListener('dragstart', (event) => {
    event.dataTransfer.setData('text/plain', conversation.key + '|' + conversation.branch);
    event.dataTransfer.effectAllowed = 'move';
  });
  return li;
}

function makeDropTarget(element, folderId) {
  element.addEventListener('dragover', (event) => {
    event.preventDefault();
    element.classList.add('drop');
  });
  element.addEventListener('dragleave', () => element.classList.remove('drop'));
  element.addEventListener('drop', (event) => {
    event.preventDefault();
    element.classList.remove('drop');
    const data = event.dataTransfer.getData('text/plain');
    if (!data) return;
    const parts = data.split('|');
    assignConversation({ key: parts[0], branch: Number(parts[1]) }, folderId);
  });
}

async function assignConversation(conversation, folderId) {
  const response = await fetch(
    '/api/conversations/' + encodeURIComponent(conversation.key) + '/folder',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ branch: conversation.branch, folder: folderId }),
    },
  );
  if (!response.ok) {
    const result = await response.json();
    window.alert('Move failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
}

async function createFolder(parent) {
  const name = window.prompt(parent ? 'New subfolder name' : 'New folder name');
  if (name === null || !name.trim()) return;
  const response = await fetch('/api/folders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.trim(), parent: parent || '' }),
  });
  if (!response.ok) {
    const result = await response.json();
    window.alert('Create failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
}

async function renameFolder(folder) {
  const name = window.prompt('New folder name', folder.name);
  if (name === null || !name.trim()) return;
  const response = await fetch('/api/folders/' + encodeURIComponent(folder.id), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.trim() }),
  });
  if (!response.ok) {
    const result = await response.json();
    window.alert('Rename failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
}

async function deleteFolder(folder) {
  if (!window.confirm('Delete folder "' + folder.name + '"? Its Conversations move to the parent folder.')) return;
  const response = await fetch('/api/folders/' + encodeURIComponent(folder.id), { method: 'DELETE' });
  if (!response.ok) {
    const result = await response.json();
    window.alert('Delete failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
}

function renderLabel(mode) {
  return mode === 'plain_code'
    ? 'Rendering: plain code blocks (click to change)'
    : 'Rendering: normal markdown (click to change)';
}

let renderTarget = null;

function chooseRender(folder) {
  renderTarget = folder;
  document.getElementById('render-picker-title').textContent = 'Rendering — ' + folderPath(folder.id);
  for (const radio of document.querySelectorAll('input[name="render-mode"]')) {
    radio.checked = radio.value === (folder.render || 'normal');
  }
  document.getElementById('render-picker').showModal();
}

async function saveRender() {
  if (!renderTarget) return;
  const picked = document.querySelector('input[name="render-mode"]:checked');
  const mode = picked ? picked.value : 'normal';
  const response = await fetch(
    '/api/folders/' + encodeURIComponent(renderTarget.id) + '/render',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode }),
    },
  );
  document.getElementById('render-picker').close();
  if (!response.ok) {
    const result = await response.json();
    window.alert('Render setting failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
}

async function moveConversation(conversation) {
  const current = folderPath(conversation.folder || '');
  const known = folders.map((folder) => folderPath(folder.id)).filter(Boolean).join(', ') || '(none)';
  const target = window.prompt('Move to folder path (empty = Unfiled).\\nAvailable: ' + known, current);
  if (target === null) return;
  const folderId = resolveFolderPath(target);
  if (folderId === null) {
    window.alert('No such folder: ' + target);
    return;
  }
  await assignConversation(conversation, folderId);
}

let pickerTargets = [];

function moveSelected() {
  const chosen = selectedConversations();
  if (chosen.length === 0) {
    setConvStatus('Select at least one Conversation first.');
    return;
  }
  const select = document.getElementById('folder-picker-select');
  select.replaceChildren();
  const root = document.createElement('option');
  root.value = '';
  root.textContent = 'Unfiled';
  select.appendChild(root);
  for (const folder of folders) {
    const option = document.createElement('option');
    option.value = folder.id;
    option.textContent = folderPath(folder.id);
    select.appendChild(option);
  }
  pickerTargets = chosen;
  document.getElementById('folder-picker').showModal();
}

async function confirmMove() {
  const folderId = document.getElementById('folder-picker-select').value;
  document.getElementById('folder-picker').close();
  for (const conversation of pickerTargets) {
    await assignConversation(conversation, folderId);
  }
  pickerTargets = [];
}

async function view(conversation) {
  const response = await fetch(
    '/api/conversations/' + encodeURIComponent(conversation.key) +
    '/content?branch=' + encodeURIComponent(conversation.branch),
  );
  const result = await response.json();
  if (!response.ok) {
    window.alert('View failed: ' + (result.error || response.status));
    return;
  }
  document.getElementById('viewer-title').textContent = result.name;
  document.getElementById('viewer-body').innerHTML = result.html || result.content;
  document.getElementById('viewer').showModal();
}

async function rename(conversation) {
  const name = window.prompt('New name', conversation.name);
  if (name === null || !name.trim()) return;
  const response = await fetch(
    '/api/conversations/' + encodeURIComponent(conversation.key) + '/rename',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim(), branch: conversation.branch }),
    },
  );
  const result = await response.json();
  if (!response.ok) {
    window.alert('Rename failed: ' + (result.error || response.status));
  }
  await loadConversations();
}

async function removeConversation(conversation) {
  if (!window.confirm('Delete \\"' + conversation.name + '\\" permanently? This cannot be undone.')) return;
  const response = await fetch(
    '/api/conversations/' + encodeURIComponent(conversation.key) +
    '?branch=' + encodeURIComponent(conversation.branch),
    { method: 'DELETE' },
  );
  const result = await response.json();
  if (!response.ok) {
    window.alert('Delete failed: ' + (result.error || response.status));
    return;
  }
  await loadConversations();
  await loadEpub();
}

function applyFilter() {
  const query = document.getElementById('filter').value.trim().toLowerCase();
  for (const row of document.querySelectorAll('#conv-tree li.conv-row')) {
    row.hidden = query ? !row.textContent.toLowerCase().includes(query) : false;
  }
  for (const node of document.querySelectorAll('#conv-tree li.folder-node')) {
    if (!query) {
      node.hidden = false;
      continue;
    }
    node.hidden = !node.querySelector('li.conv-row:not([hidden])');
  }
}

function updateSelectedCount() {
  const count = document.querySelectorAll('#conv-tree .conv-check:checked').length;
  document.getElementById('conv-selected').textContent = count ? count + ' selected' : '';
}

function setEpubStatus(message) {
  document.getElementById('epub-status').textContent = message;
}

function rootOf(path) {
  return path.split('/')[0];
}

function joinPath(parent, name) {
  return parent ? parent + '/' + name : name;
}

function parentOf(path) {
  return path.split('/').slice(0, -1).join('/');
}

function renderNode(node, depth) {
  const li = document.createElement('li');

  if (node.type === 'dir') {
    const details = document.createElement('details');
    details.open = depth === 0;
    const summary = document.createElement('summary');
    summary.className = 'node-row dir';
    const chev = icon('chevron', 'chev');
    summary.appendChild(chev);
    const folder = icon('folder', 'node-icon');
    summary.appendChild(folder);
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = node.name;
    summary.appendChild(name);

    const actions = document.createElement('span');
    actions.className = 'actions';
    const root = rootOf(node.path);
    if (root === 'inbox' || root === 'out') {
      actions.appendChild(iconButton('folder-plus', 'New folder', () => newFolder(node.path)));
      actions.appendChild(iconButton('download', 'Download folder', () => downloadFolder(node)));
      if (node.path.split('/').length > 1) {
        actions.appendChild(iconButton('pencil', 'Rename', () => renameFolderPath(node.path)));
        actions.appendChild(iconButton('trash', 'Delete', () => deleteFolderPath(node.path), true));
      }
    }
    summary.appendChild(actions);
    details.appendChild(summary);

    const ul = document.createElement('ul');
    ul.className = 'tree';
    for (const child of node.children) {
      ul.appendChild(renderNode(child, depth + 1));
    }
    details.appendChild(ul);
    li.appendChild(details);
    return li;
  }

  const row = document.createElement('span');
  row.className = 'node-row file';
  const file = icon('file', 'node-icon');
  row.appendChild(file);
  const name = document.createElement('span');
  name.className = 'name';
  name.textContent = node.name;
  name.title = node.name;
  row.appendChild(name);

  const actions = document.createElement('span');
  actions.className = 'actions';
  const root = rootOf(node.path);
  if (node.path.toLowerCase().endsWith('.epub')) {
    if (root === 'inbox') {
      actions.appendChild(iconButton('convert', 'Convert', () => convertPath(node.path)));
    }
    if (root === 'inbox' || root === 'out') {
      actions.appendChild(iconButton('download', 'Download', () => downloadFile(node.path)));
    }
  }
  if (root === 'inbox' || root === 'out') {
    actions.appendChild(iconButton('move', 'Move', () => moveFile(node.path)));
    actions.appendChild(iconButton('trash', 'Delete', () => deleteFile(node.path), true));
  }
  row.appendChild(actions);
  li.appendChild(row);
  return li;
}

async function loadEpub() {
  const response = await fetch('/api/epub/tree');
  const body = await response.json();
  const container = document.getElementById('epub-tree');
  container.replaceChildren();
  for (const root of body.roots || []) {
    const ul = document.createElement('ul');
    ul.className = 'tree root';
    ul.appendChild(renderNode(root, 0));
    container.appendChild(ul);
  }
}

async function epubAction(method, url, body) {
  const options = { method: method };
  if (body !== undefined) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  let result = {};
  try { result = await response.json(); } catch (error) { result = {}; }
  if (!response.ok) {
    setEpubStatus('Failed: ' + (result.error || response.status));
  } else {
    setEpubStatus('Done.');
  }
  await loadEpub();
  return response.ok;
}

async function newFolder(path) {
  const name = window.prompt('New folder name');
  if (name === null || !name.trim()) return;
  await epubAction('POST', '/api/epub/folder', { path: joinPath(path, name.trim()) });
}

async function renameFolderPath(path) {
  const name = window.prompt('New folder name', path.split('/').pop());
  if (name === null || !name.trim()) return;
  await epubAction('POST', '/api/epub/folder/rename', {
    from: path, to: joinPath(parentOf(path), name.trim()),
  });
}

async function deleteFolderPath(path) {
  if (!window.confirm('Delete folder "' + path + '" and everything inside it?')) return;
  await epubAction('DELETE', '/api/epub/folder?path=' + encodeURIComponent(path));
}

async function deleteFile(path) {
  if (!window.confirm('Delete "' + path + '"?')) return;
  await epubAction('DELETE', '/api/epub/file?path=' + encodeURIComponent(path));
}

async function moveFile(path) {
  const target = window.prompt('Move to (full path within ' + rootOf(path) + ')', path);
  if (target === null || !target.trim() || target === path) return;
  await epubAction('POST', '/api/epub/move', { from: path, to: target.trim() });
}

function downloadFile(path) {
  window.location = '/api/epub/file?path=' + encodeURIComponent(path);
}

function folderEpubs(node) {
  if (node.type === 'file') {
    return node.path.toLowerCase().endsWith('.epub') ? [node.path] : [];
  }
  const paths = [];
  for (const child of node.children || []) {
    paths.push(...folderEpubs(child));
  }
  return paths;
}

function downloadFolder(node) {
  for (const path of folderEpubs(node)) {
    const link = document.createElement('a');
    link.href = '/api/epub/file?path=' + encodeURIComponent(path);
    link.download = path.split('/').pop();
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
}

async function convertPath(path) {
  const response = await fetch('/api/epub/convert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: path }),
  });
  const result = await response.json();
  if (response.ok) {
    if (result.converted) {
      setEpubStatus('Converted ' + result.converted.length + ', failed ' + result.failed.length);
    } else {
      setEpubStatus('Converted ' + result.input + ' -> ' + result.output);
    }
  } else {
    setEpubStatus('Failed: ' + (result.error || response.status));
  }
  await loadEpub();
}

async function scan() {
  const response = await fetch('/api/epub/scan', { method: 'POST' });
  const result = await response.json();
  setEpubStatus('Converted ' + result.converted.length + ', failed ' + result.failed.length);
  await loadEpub();
}

async function upload() {
  const input = document.getElementById('epub-upload');
  const status = document.getElementById('upload-status');
  if (!input.files.length) {
    status.textContent = 'Choose an EPUB first.';
    return;
  }
  const file = input.files[0];
  let url = '/api/epub/upload?name=' + encodeURIComponent(file.name);
  const dir = document.getElementById('upload-dir').value.trim();
  if (dir) url += '&dir=' + encodeURIComponent(dir);
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/epub+zip' },
    body: file,
  });
  const result = await response.json();
  if (response.ok) {
    status.textContent = 'Uploaded ' + result.name;
    input.value = '';
  } else {
    status.textContent = 'Failed: ' + (result.error || response.status);
  }
  await loadEpub();
}

function selectedConversations() {
  const selected = [];
  for (const checkbox of document.querySelectorAll('#conv-tree .conv-check:checked')) {
    selected.push({ key: checkbox.dataset.key, branch: Number(checkbox.dataset.branch) });
  }
  return selected;
}

async function buildEpub() {
  const chosen = selectedConversations();
  const status = document.getElementById('build-status');
  if (chosen.length === 0) {
    status.textContent = 'Select at least one Conversation.';
    return;
  }
  const title = document.getElementById('build-title').value.trim();
  const body = { conversations: chosen };
  if (title) body.title = title;
  const response = await fetch('/api/epub/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (response.ok) {
    status.textContent = 'Built ' + result.output;
  } else {
    status.textContent = 'Failed: ' + (result.error || response.status);
  }
  await loadEpub();
}

function setWorkStatus(message) {
  document.getElementById('work-status').textContent = message;
}

async function loadWorkList() {
  const response = await fetch('/api/epub/work');
  const body = await response.json();
  const list = document.getElementById('work-list');
  list.replaceChildren();
  for (const copy of body.work || []) {
    const link = document.createElement('a');
    link.textContent = copy.name;
    link.title = copy.name;
    link.addEventListener('click', () => selectWork(copy.id, copy.name));
    list.appendChild(link);
  }
  if (!list.childNodes.length) list.textContent = 'none yet';
}

async function selectWork(id, name) {
  document.getElementById('work-id').value = id;
  document.getElementById('work-name').value = name || '';
  await loadWork();
}

async function createWork() {
  const chosen = selectedConversations();
  if (chosen.length === 0) {
    setWorkStatus('Select at least one Conversation.');
    return;
  }
  const body = { conversations: chosen };
  const name = document.getElementById('work-name').value.trim();
  if (name) body.name = name;
  const response = await fetch('/api/epub/work', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) {
    setWorkStatus('Failed: ' + (result.error || response.status));
    return;
  }
  document.getElementById('work-id').value = result.id;
  document.getElementById('work-name').value = result.name || '';
  document.getElementById('work-content').value = result.content;
  setWorkStatus('Created work copy.');
  await loadWorkList();
  renderOutline();
}

function currentWorkId() {
  const id = document.getElementById('work-id').value.trim();
  if (!id) setWorkStatus('Select a work copy first.');
  return id;
}

async function loadWork() {
  const id = currentWorkId();
  if (!id) return;
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id));
  const result = await response.json();
  if (!response.ok) {
    setWorkStatus('Failed: ' + (result.error || response.status));
    return;
  }
  document.getElementById('work-content').value = result.content;
  setWorkStatus('Loaded work copy.');
  renderOutline();
}

async function renameWork() {
  const id = currentWorkId();
  if (!id) return;
  const name = document.getElementById('work-name').value.trim();
  if (!name) {
    setWorkStatus('Enter a name.');
    return;
  }
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name }),
  });
  if (response.ok) {
    setWorkStatus('Renamed.');
    await loadWorkList();
  } else {
    const result = await response.json();
    setWorkStatus('Failed: ' + (result.error || response.status));
  }
}

async function saveWork() {
  const id = currentWorkId();
  if (!id) return;
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: document.getElementById('work-content').value }),
  });
  const result = await response.json();
  setWorkStatus(response.ok ? 'Saved.' : 'Failed: ' + (result.error || response.status));
}

function downloadWork() {
  const id = currentWorkId();
  if (!id) return;
  window.location = '/api/epub/work/' + encodeURIComponent(id) + '/download';
}

async function buildWork() {
  const id = currentWorkId();
  if (!id) return;
  const response = await fetch('/api/epub/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ work: id }),
  });
  const result = await response.json();
  if (response.ok) {
    setWorkStatus('Built ' + result.output);
  } else {
    setWorkStatus('Failed: ' + (result.error || response.status));
  }
  await loadEpub();
}

async function discardWork() {
  const id = currentWorkId();
  if (!id) return;
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id), { method: 'DELETE' });
  const result = await response.json();
  if (response.ok) {
    document.getElementById('work-id').value = '';
    document.getElementById('work-name').value = '';
    document.getElementById('work-content').value = '';
    document.getElementById('work-outline').replaceChildren();
    setWorkStatus('Discarded.');
    await loadWorkList();
  } else {
    setWorkStatus('Failed: ' + (result.error || response.status));
  }
}

function renderOutline() {
  const content = document.getElementById('work-content').value;
  const container = document.getElementById('work-outline');
  const chapters = [];
  content.split('\\n').forEach((line, index) => {
    const match = line.match(/^#\\s+(.*)$/);
    if (match && match[1].trim()) {
      chapters.push({ title: match[1].trim(), index: index });
    }
  });
  container.replaceChildren();
  if (chapters.length === 0) {
    const note = document.createElement('p');
    note.className = 'muted';
    note.textContent = 'No chapters (# headings) yet.';
    container.appendChild(note);
    return;
  }
  const heading = document.createElement('p');
  heading.className = 'muted';
  heading.textContent = chapters.length + ' chapter(s):';
  container.appendChild(heading);
  const ul = document.createElement('ul');
  for (const chapter of chapters) {
    const li = document.createElement('li');
    const link = document.createElement('a');
    link.textContent = chapter.title;
    link.addEventListener('click', () => jumpToLine(chapter.index));
    li.appendChild(link);
    ul.appendChild(li);
  }
  container.appendChild(ul);
}

function jumpToLine(lineIndex) {
  const textarea = document.getElementById('work-content');
  const lines = textarea.value.split('\\n');
  let offset = 0;
  for (let i = 0; i < lineIndex && i < lines.length; i += 1) {
    offset += lines[i].length + 1;
  }
  textarea.focus();
  textarea.selectionStart = textarea.selectionEnd = offset;
}

document.getElementById('viewer-close').addEventListener('click', () => {
  document.getElementById('viewer').close();
});
document.getElementById('conv-new-folder').addEventListener('click', () => createFolder(''));
document.getElementById('conv-move-selected').addEventListener('click', moveSelected);
document.getElementById('folder-picker-cancel').addEventListener('click', () => {
  document.getElementById('folder-picker').close();
});
document.getElementById('folder-picker-ok').addEventListener('click', confirmMove);
document.getElementById('render-picker-cancel').addEventListener('click', () => {
  document.getElementById('render-picker').close();
});
document.getElementById('render-picker-ok').addEventListener('click', saveRender);
document.getElementById('scan').addEventListener('click', scan);
document.getElementById('upload').addEventListener('click', upload);
document.getElementById('filter').addEventListener('input', applyFilter);
document.getElementById('select-all').addEventListener('change', (event) => {
  for (const checkbox of document.querySelectorAll('#conv-tree .conv-check')) {
    checkbox.checked = event.target.checked;
  }
  updateSelectedCount();
});
document.getElementById('build').addEventListener('click', buildEpub);
document.getElementById('work-create').addEventListener('click', createWork);
document.getElementById('work-refresh').addEventListener('click', loadWorkList);
document.getElementById('work-rename').addEventListener('click', renameWork);
document.getElementById('work-save').addEventListener('click', saveWork);
document.getElementById('work-download').addEventListener('click', downloadWork);
document.getElementById('work-build').addEventListener('click', buildWork);
document.getElementById('work-discard').addEventListener('click', discardWork);
document.getElementById('work-content').addEventListener('input', renderOutline);

loadConversations();
loadEpub();
loadWorkList();
</script>
</body>
</html>
"""
