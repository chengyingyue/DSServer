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

load();
</script>
</body>
</html>
"""
