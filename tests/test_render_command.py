from __future__ import annotations

from typing import Any

from dsserver.markdown import render_all

from .conftest import build_app, chat_response, client_for, conversation_files, sequence_handler


async def _capture_two_turns(config) -> None:
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("6")]))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    request1 = {"model": "deepseek-flash", "messages": messages}
    request2 = {
        "model": "deepseek-flash",
        "messages": messages
        + [{"role": "assistant", "content": "4"}, {"role": "user", "content": "And 3+3?"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request1)
        await client.post("/chat/completions", json=request2)


async def test_render_reproduces_incrementally_written_markdown(config):
    await _capture_two_turns(config)
    before = {path.name: path.read_text(encoding="utf-8") for path in conversation_files(config)}
    index_before = config.index_path.read_text(encoding="utf-8")

    for path in conversation_files(config):
        path.unlink()
    config.index_path.unlink()

    count = render_all(config)

    after = {path.name: path.read_text(encoding="utf-8") for path in conversation_files(config)}
    assert count == 1
    assert after == before
    assert config.index_path.read_text(encoding="utf-8") == index_before


async def test_render_never_modifies_the_jsonl_log(config):
    await _capture_two_turns(config)
    log_before = config.log_path.read_text(encoding="utf-8")

    render_all(config)

    assert config.log_path.read_text(encoding="utf-8") == log_before
