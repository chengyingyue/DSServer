# 06: Run the Bridge on the home LAN

**What to build:** The owner can start the Bridge on their PC and use it from the phone app on the same Wi-Fi, with captured records appearing in the store directory. Includes the default configuration, the start command, and guidance for fixed LAN IP, Windows firewall, and autostart.

**Blocked by:** 01.

**Status:** done

- [x] Default configuration binds `0.0.0.0:8787`, with a documented start command.
- [x] A phone on the same Wi-Fi, its app base URL pointed at the Bridge, gets working chat responses.
- [x] After real phone use, captured records appear in the store directory and render into Markdown.
- [x] Instructions cover a fixed LAN IP, the Windows firewall inbound rule, and autostart on login.

## Comments

- Verified done: `config.toml` and `README.md` (§Run, §Home LAN setup); the prod/test port split is covered by `tests/test_config.py` and `tests/test_port_guard.py`.
