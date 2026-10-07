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
    <tr><th>Name</th><th>Date</th><th>Turns</th><th></th></tr>
  </thead>
  <tbody id="rows"></tbody>
</table>

<h1>EPUB</h1>
<p class="muted">Convert EPUBs from the inbox into e-reader friendly copies in the outbox.</p>
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
<script>
async function load() {
  const response = await fetch('/api/conversations');
  const conversations = await response.json();
  const rows = document.getElementById('rows');
  rows.replaceChildren();
  for (const conversation of conversations) {
    const tr = document.createElement('tr');

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

document.getElementById('scan').addEventListener('click', scan);

load();
loadEpub();
</script>
</body>
</html>
"""
