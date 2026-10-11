
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
  const trimmed = (path || '').trim().replace(/^\/+|\/+$/g, '');
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
  meta.textContent = conversation.date + ' \u00b7 ' + conversation.turns;
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
  const target = window.prompt('Move to folder path (empty = Unfiled).\nAvailable: ' + known, current);
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
  if (!window.confirm('Delete \"' + conversation.name + '\" permanently? This cannot be undone.')) return;
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
  content.split('\n').forEach((line, index) => {
    const match = line.match(/^#\s+(.*)$/);
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
  const lines = textarea.value.split('\n');
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
