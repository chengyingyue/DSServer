from __future__ import annotations

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DSServer</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 56rem; padding: 0 1rem; }
  h1 { font-size: 1.4rem; }
  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #ddd; vertical-align: top; }
  button { cursor: pointer; }
  .muted { color: #777; }
</style>
</head>
<body>
<h1>Conversations</h1>
<p class="muted">Rename a Conversation to choose its Markdown filename.</p>
<table>
  <thead>
    <tr><th></th><th>Name</th><th>Date</th><th>Turns</th><th></th></tr>
  </thead>
  <tbody id="rows"></tbody>
</table>

<h1>EPUB</h1>
<p class="muted">Tick Conversations and build one EPUB, or convert EPUBs from the inbox into e-reader friendly copies in the outbox.</p>
<p>
  <input id="build-title" type="text" placeholder="Book title (optional)">
  <button id="build">Build EPUB</button>
  <span class="muted" id="build-status"></span>
</p>
<p><button id="scan">Scan inbox</button> <span class="muted" id="epub-status"></span></p>
<table>
  <thead>
    <tr><th>Inbox</th><th></th></tr>
  </thead>
  <tbody id="epub-inbox"></tbody>
</table>
<table>
  <thead>
    <tr><th>Out</th></tr>
  </thead>
  <tbody id="epub-out"></tbody>
</table>

<h1>Work copy</h1>
<p class="muted">Create an editable copy of the ticked Conversations, refine it, build an EPUB from it, then discard it. Editing never changes the original Conversations or the log.</p>
<p>
  <button id="work-create">Create from selection</button>
  <button id="work-load">Load</button>
  <button id="work-save">Save</button>
  <button id="work-build">Build EPUB</button>
  <button id="work-discard">Discard</button>
  <span class="muted" id="work-status"></span>
</p>
<p><input id="work-id" type="text" placeholder="Work copy id" size="40"></p>
<p><textarea id="work-content" rows="16" cols="80"></textarea></p>
<script>
async function load() {
  const response = await fetch('/api/conversations');
  const conversations = await response.json();
  const rows = document.getElementById('rows');
  rows.replaceChildren();
  for (const conversation of conversations) {
    const tr = document.createElement('tr');

    const select = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.dataset.key = conversation.key;
    checkbox.dataset.branch = String(conversation.branch);
    select.appendChild(checkbox);
    tr.appendChild(select);

    const name = document.createElement('td');
    name.textContent = conversation.name;
    tr.appendChild(name);

    const date = document.createElement('td');
    date.textContent = conversation.date;
    tr.appendChild(date);

    const turns = document.createElement('td');
    turns.textContent = conversation.turns;
    tr.appendChild(turns);

    const actions = document.createElement('td');
    const button = document.createElement('button');
    button.textContent = 'Rename';
    button.addEventListener('click', () => rename(conversation));
    actions.appendChild(button);
    tr.appendChild(actions);

    rows.appendChild(tr);
  }
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
  if (!response.ok) {
    window.alert('Rename failed: ' + response.status);
  }
  await load();
}

function setEpubStatus(message) {
  document.getElementById('epub-status').textContent = message;
}

async function loadEpub() {
  const response = await fetch('/api/epub/files');
  const files = await response.json();

  const inbox = document.getElementById('epub-inbox');
  inbox.replaceChildren();
  for (const name of files.inbox) {
    const tr = document.createElement('tr');

    const file = document.createElement('td');
    file.textContent = name;
    tr.appendChild(file);

    const actions = document.createElement('td');
    const button = document.createElement('button');
    button.textContent = 'Convert';
    button.addEventListener('click', () => convert(name));
    actions.appendChild(button);
    tr.appendChild(actions);

    inbox.appendChild(tr);
  }

  const out = document.getElementById('epub-out');
  out.replaceChildren();
  for (const name of files.out) {
    const tr = document.createElement('tr');
    const file = document.createElement('td');
    file.textContent = name;
    tr.appendChild(file);
    out.appendChild(tr);
  }
}

async function convert(name) {
  const response = await fetch('/api/epub/convert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name }),
  });
  const result = await response.json();
  if (response.ok) {
    setEpubStatus('Converted ' + result.input + ' -> ' + result.output);
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

function selectedConversations() {
  const selected = [];
  for (const checkbox of document.querySelectorAll('#rows input[type=checkbox]:checked')) {
    selected.push({ key: checkbox.dataset.key, branch: Number(checkbox.dataset.branch) });
  }
  return selected;
}

async function buildEpub() {
  const conversations = selectedConversations();
  const status = document.getElementById('build-status');
  if (conversations.length === 0) {
    status.textContent = 'Select at least one Conversation.';
    return;
  }
  const title = document.getElementById('build-title').value.trim();
  const body = { conversations: conversations };
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

async function createWork() {
  const conversations = selectedConversations();
  if (conversations.length === 0) {
    setWorkStatus('Select at least one Conversation.');
    return;
  }
  const response = await fetch('/api/epub/work', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversations: conversations }),
  });
  const result = await response.json();
  if (!response.ok) {
    setWorkStatus('Failed: ' + (result.error || response.status));
    return;
  }
  document.getElementById('work-id').value = result.id;
  document.getElementById('work-content').value = result.content;
  setWorkStatus('Created work copy.');
}

async function loadWork() {
  const id = document.getElementById('work-id').value.trim();
  if (!id) {
    setWorkStatus('Enter a work copy id.');
    return;
  }
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id));
  const result = await response.json();
  if (!response.ok) {
    setWorkStatus('Failed: ' + (result.error || response.status));
    return;
  }
  document.getElementById('work-content').value = result.content;
  setWorkStatus('Loaded work copy.');
}

async function saveWork() {
  const id = document.getElementById('work-id').value.trim();
  if (!id) {
    setWorkStatus('Enter a work copy id.');
    return;
  }
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: document.getElementById('work-content').value }),
  });
  const result = await response.json();
  setWorkStatus(response.ok ? 'Saved.' : 'Failed: ' + (result.error || response.status));
}

async function buildWork() {
  const id = document.getElementById('work-id').value.trim();
  if (!id) {
    setWorkStatus('Enter a work copy id.');
    return;
  }
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
  const id = document.getElementById('work-id').value.trim();
  if (!id) {
    setWorkStatus('Enter a work copy id.');
    return;
  }
  const response = await fetch('/api/epub/work/' + encodeURIComponent(id), { method: 'DELETE' });
  const result = await response.json();
  if (response.ok) {
    document.getElementById('work-id').value = '';
    document.getElementById('work-content').value = '';
    setWorkStatus('Discarded.');
  } else {
    setWorkStatus('Failed: ' + (result.error || response.status));
  }
}

document.getElementById('scan').addEventListener('click', scan);
document.getElementById('build').addEventListener('click', buildEpub);
document.getElementById('work-create').addEventListener('click', createWork);
document.getElementById('work-load').addEventListener('click', loadWork);
document.getElementById('work-save').addEventListener('click', saveWork);
document.getElementById('work-build').addEventListener('click', buildWork);
document.getElementById('work-discard').addEventListener('click', discardWork);

load();
loadEpub();
</script>
</body>
</html>
"""
