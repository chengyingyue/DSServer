from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .conftest import build_app, chat_response, client_for, conversation_files, sequence_handler

OLD = 1_000_000.0


def _find_file(config, needle: str) -> Path:
    for path in conversation_files(config):
        if needle in path.read_text(encoding="utf-8"):
            return path
    raise AssertionError(f"no conversation file contains {needle!r}")


async def test_a_new_message_only_rewrites_its_own_conversation(config):
    app = build_app(
        config,
        sequence_handler(
            [
                chat_response("alpha answer"),
                chat_response("beta answer"),
                chat_response("alpha answer two"),
            ]
        ),
    )
    alpha_1: dict[str, Any] = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "alpha question"}],
    }
    beta: dict[str, Any] = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "beta question"}],
    }
    alpha_2: dict[str, Any] = {
        "model": "deepseek-flash",
        "messages": alpha_1["messages"]
        + [
            {"role": "assistant", "content": "alpha answer"},
            {"role": "user", "content": "alpha followup"},
        ],
    }

    async with client_for(app) as client:
        await client.post("/chat/completions", json=alpha_1)
        await client.post("/chat/completions", json=beta)

        untouched = _find_file(config, "beta question")
        content_before = untouched.read_text(encoding="utf-8")
        os.utime(untouched, (OLD, OLD))
        mtime_before = untouched.stat().st_mtime

        await client.post("/chat/completions", json=alpha_2)

    assert untouched.read_text(encoding="utf-8") == content_before
    assert untouched.stat().st_mtime == mtime_before
    assert "alpha followup" in _find_file(config, "alpha question").read_text(encoding="utf-8")


async def test_unchanged_markdown_is_not_rewritten(config):
    from dsserver.markdown import render_all

    app = build_app(config, sequence_handler([chat_response("4")]))
    async with client_for(app) as client:
        await client.post(
            "/chat/completions",
            json={"messages": [{"role": "user", "content": "What is 2+2?"}]},
        )

    conversation = conversation_files(config)[0]
    os.utime(conversation, (OLD, OLD))
    os.utime(config.index_path, (OLD, OLD))
    mtime_conversation = conversation.stat().st_mtime
    mtime_index = config.index_path.stat().st_mtime

    render_all(config)

    assert conversation.stat().st_mtime == mtime_conversation
    assert config.index_path.stat().st_mtime == mtime_index
