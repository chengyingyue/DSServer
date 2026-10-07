# DSServer

A local, self-hosted **Bridge** that sits between an OpenAI-compatible Client and
DeepSeek. It forwards traffic byte-for-byte, records every chat Exchange to an
append-only JSONL log, and renders human-readable Markdown conversations that
clearly separate app-injected (system) prompts from human input.

## Requirements

- Python 3.11+ (managed automatically by `uv`)
- [uv](https://docs.astral.sh/uv/)

## Install

```
uv sync
```

## Configure

Edit `config.toml`:

```toml
upstream_base_url = "https://api.deepseek.com"
bind = "0.0.0.0"            # listen on the LAN; use 127.0.0.1 for local-only
port = 8787
deep_paths = ["/chat/completions", "/v1/chat/completions"]
store_dir = "data"
keep_raw_sse = true
```

## Run

```
uv run dsserver
```

Point your Client's API base URL at the Bridge, for example
`http://192.168.1.50:8787` (or `http://192.168.1.50:8787/v1`). The Client keeps
sending its own API key; the Bridge passes it through and never stores it.

### Run in the background (no terminal left open)

To keep the Bridge running without leaving a terminal window open, start it as a
hidden process that logs to files:

```powershell
Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run", "dsserver" `
  -RedirectStandardOutput "dsserver.log" -RedirectStandardError "dsserver.err.log"
```

Check it is running and stop it when needed:

```powershell
Get-Process -Name dsserver
Stop-Process -Name dsserver
```

## Rebuild the reading view

Markdown is derived from the JSONL log and can be regenerated at any time:

```
uv run dsserver render
```

## Where the data lives

- `data/exchanges.jsonl` — the append-only truth log, one Exchange per line
- `data/conversations/*.md` — the Markdown reading view
- `data/index.md` — the list of conversations

## Home LAN setup

1. **Fixed LAN IP** — reserve a DHCP lease for the PC in your router, or assign a
   static IP, so the Client's base URL does not change.
2. **Windows firewall** — allow inbound TCP 8787 on the private network:

   ```powershell
   New-NetFirewallRule -DisplayName "DSServer" -Direction Inbound -Protocol TCP -LocalPort 8787 -Action Allow -Profile Private
   ```

3. **Autostart on login** — create a shortcut to
   `uv run dsserver` (working directory = this repo) in `shell:startup`, or
   register it with Task Scheduler.

## Going remote later

To use the Bridge from outside the home, put it behind a free
[Tailscale](https://tailscale.com/) network; no code or configuration change is
needed. See `Tailscale 配置指南.md` for the full setup steps.
