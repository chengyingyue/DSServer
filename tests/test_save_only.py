from __future__ import annotations

import json

from .conftest import (
    BrokenTokenCounter,
    build_app,
    chat_response,
    client_for,
    read_records,
    sequence_handler,
)
from dsserver.markdown import ConversationIndex
from dsserver.models import (
    CHAT_KIND,
    SAVE_KIND,
    build_chat_response,
    build_client_info,
    build_exchange,
)


def _no_upstream(request):
    raise AssertionError("save-only request must not reach the Upstream")


async def test_save_records_without_forwarding_and_returns_marker(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-flash",
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "Remember this."},
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Remember this.\nsaved · 4 tokens"

    records = read_records(config)
    assert len(records) == 1
    assert records[0]["kind"] == "save"
    assert records[0]["response"]["message"]["content"] == "Remember this.\nsaved · 4 tokens"
    assert records[0]["request"]["messages"] == request["messages"]


async def test_save_accepts_the_canonical_completions_path(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        response = await client.post("/save/chat/completions", json=request)

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Remember this.\nsaved · 2 tokens"


async def test_save_echoes_only_the_latest_user_message(config):
    app = build_app(config, _no_upstream)
    request = {
        "messages": [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "Second question\nsaved · 6 tokens"


async def test_save_without_user_message_returns_plain_marker(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "system", "content": "Be terse."}]}
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "saved · 2 tokens"


async def test_save_with_non_text_user_content_returns_plain_marker(config):
    app = build_app(config, _no_upstream)
    request = {
        "messages": [
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x"}}]}
        ],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.json()["choices"][0]["message"]["content"] == "saved · 0 tokens"


async def test_saved_conversation_appears_in_markdown(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)

    files = sorted(config.conversations_dir.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "Remember this.\nsaved · 2 tokens" in text
    assert "Remember this." in text


async def test_save_names_the_conversation_after_the_last_user_message(config):
    app = build_app(config, _no_upstream)
    request = {
        "messages": [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "I need help with returns"},
        ]
    }
    async with client_for(app) as client:
        await client.post("/save", json=request)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "I need help with returns"
    assert entry["filename"].endswith("-i-need-help-with-returns.md")
    text = (config.conversations_dir / entry["filename"]).read_text(encoding="utf-8")
    assert text.startswith("# I need help with returns")


async def test_save_truncates_a_long_last_message_on_a_word_boundary(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "word " * 30}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == " ".join(["word"] * 12)
    assert len(entry["title"]) <= 60


async def test_save_truncates_an_unbroken_last_message_to_the_limit(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "长" * 100}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "长" * 60
    assert len(entry["title"]) == 60


async def test_save_falls_back_to_conversation_when_last_message_is_empty(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "   "}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "Conversation"


async def test_save_flattens_non_string_last_message_content(config):
    app = build_app(config, _no_upstream)
    parts = [{"type": "text", "text": "Help with returns"}]
    request = {"messages": [{"role": "user", "content": parts}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)
        entry = (await client.get("/api/conversations")).json()[0]

    assert "Help with returns" in entry["title"]
    assert len(entry["title"]) <= 60


async def test_save_numbers_colliding_names(config):
    app = build_app(config, _no_upstream)
    request = {"messages": [{"role": "user", "content": "Same question"}]}
    async with client_for(app) as client:
        await client.post("/save", json=request)
        await client.post("/save", json=request)
        entries = (await client.get("/api/conversations")).json()

    assert len(entries) == 2
    assert {entry["title"] for entry in entries} == {"Same question"}
    names = {path.name for path in config.conversations_dir.glob("*.md")}
    date = next(iter(names))[:10]
    assert names == {f"{date}-same-question.md", f"{date}-same-question-2.md"}


async def test_regular_chat_still_names_from_the_first_user_message(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("6")]))
    first = {"model": "deepseek-flash", "messages": [{"role": "user", "content": "What is 2+2?"}]}
    second = {
        "model": "deepseek-flash",
        "messages": first["messages"]
        + [{"role": "assistant", "content": "4"}, {"role": "user", "content": "And 3+3?"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=first)
        await client.post("/chat/completions", json=second)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "What is 2+2?"


async def test_save_survives_tokenizer_failure(config):
    app = build_app(config, _no_upstream, token_counter=BrokenTokenCounter())
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Remember this.\nsaved"


async def test_save_survives_tokenizer_oserror(config):
    app = build_app(
        config, _no_upstream, token_counter=BrokenTokenCounter(OSError("disk full"))
    )
    request = {"messages": [{"role": "user", "content": "Remember this."}]}
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Remember this.\nsaved"


async def test_save_rejects_invalid_body(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/save", content=json.dumps({"foo": 1}))

    assert response.status_code == 400


async def test_save_streaming_returns_sse(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-chat",
        "stream": True,
        "messages": [{"role": "user", "content": "hello test"}],
    }
    async with client_for(app) as client:
        response = await client.post("/save", json=request)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert body.endswith("data: [DONE]\n\n")

    deltas = []
    finish = None
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            continue
        chunk = json.loads(payload)
        choice = chunk["choices"][0]
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
        content = choice.get("delta", {}).get("content")
        if content:
            deltas.append(content)

    assert "".join(deltas) == "hello test\nsaved · 2 tokens"
    assert finish == "stop"


async def test_save_streaming_is_recorded_once(config):
    app = build_app(config, _no_upstream)
    request = {
        "model": "deepseek-chat",
        "stream": True,
        "messages": [{"role": "user", "content": "hello test"}],
    }
    async with client_for(app) as client:
        await client.post("/save", json=request)

    records = read_records(config)
    assert len(records) == 1
    assert records[0]["response"]["message"]["content"] == "hello test\nsaved · 2 tokens"


async def test_second_save_into_the_same_conversation_retitles_it(config):
    app = build_app(config, _no_upstream)
    first = {"messages": [{"role": "user", "content": "First"}]}
    second = {
        "messages": [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "First\nsaved · 1 tokens"},
            {"role": "user", "content": "Second"},
        ]
    }
    async with client_for(app) as client:
        await client.post("/save", json=first)
        await client.post("/save", json=second)
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "Second"


async def test_legacy_meta_saved_chat_record_still_replays_as_saved(config):
    config.store_dir.mkdir(parents=True, exist_ok=True)
    legacy = build_exchange(
        CHAT_KIND,
        build_client_info({}, []),
        {
            "messages": [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "I need help with returns"},
            ]
        },
        build_chat_response(
            200, None, "stop", {"role": "assistant", "content": "I need help with returns\nsaved"}
        ),
        {"upstream": None, "saved": True},
    )
    config.log_path.write_text(json.dumps(legacy.to_dict()) + "\n", encoding="utf-8")
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        entry = (await client.get("/api/conversations")).json()[0]

    assert entry["title"] == "I need help with returns"


def _stored_record(kind, msgs, content="ok"):
    return build_exchange(
        kind,
        build_client_info({}, []),
        {"messages": msgs, "model": "m"},
        build_chat_response(200, None, "stop", {"role": "assistant", "content": content}),
        {},
    ).to_dict()


def _index_of(records):
    return {entry.filename for entry in ConversationIndex.from_records(records).conversations}


def test_save_after_chat_on_the_same_origin_numbers_two():
    msgs = [{"role": "user", "content": "Same question"}]
    records = [_stored_record(CHAT_KIND, msgs), _stored_record(SAVE_KIND, msgs)]

    assert _index_of(records) == {
        "2026-10-20-same-question.md",
        "2026-10-20-same-question-2.md",
    }


def test_chat_branch_after_save_on_the_same_origin_keeps_branch_suffix():
    msgs = [{"role": "user", "content": "Same question"}]
    diverged = msgs + [{"role": "assistant", "content": "ok"}, {"role": "user", "content": "go on"}]
    records = [
        _stored_record(SAVE_KIND, msgs, content="different answer"),
        _stored_record(CHAT_KIND, diverged),
    ]

    assert _index_of(records) == {
        "2026-10-20-same-question.md",
        "2026-10-20-same-question-b2.md",
    }
