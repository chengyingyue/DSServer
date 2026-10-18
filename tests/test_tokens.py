from __future__ import annotations

import json

import pytest

from dsserver.tokens import (
    TokenInputError,
    count_messages,
    decode_text,
    estimate_upload,
    extract_json_text,
    extract_jsonl_text,
    messages_text,
)

from .conftest import (
    BrokenTokenCounter,
    FakeTokenCounter,
    build_app,
    client_for,
    stored_chat_response,
)


def _no_upstream(request):
    raise AssertionError("token requests must not reach the Upstream")


def test_messages_text_joins_only_text_content():
    messages = [
        {"role": "system", "content": "be terse"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "image_url", "image_url": {"url": "x"}},
            ],
        },
        {"role": "assistant", "content": None},
        {"role": "user", "content": {"type": "text", "text": "world"}},
    ]

    assert messages_text(messages) == "be terse\nhello\nworld"


def test_extract_json_text_includes_request_and_response():
    record = {
        "request": {"messages": [{"role": "user", "content": "one two"}]},
        "response": {"choices": [{"message": {"role": "assistant", "content": "three"}}]},
    }

    assert extract_json_text(record) == "one two\nthree"


def test_extract_json_text_includes_stored_response_message():
    record = {
        "request": {"messages": [{"role": "user", "content": "one two"}]},
        "response": stored_chat_response("three"),
    }

    assert extract_json_text(record) == "one two\nthree"


def test_extract_json_text_reads_plain_completion():
    completion = {
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
    }

    assert extract_json_text(completion) == "hello"


def test_extract_json_text_reads_message_list():
    assert extract_json_text([{"role": "user", "content": "hi"}]) == "hi"


def test_extract_json_text_ignores_nested_role_outside_messages():
    assert extract_json_text({"foo": {"role": "user", "content": "hi"}}) is None


def test_extract_json_text_returns_none_for_other_data():
    assert extract_json_text({"foo": ["bar"]}) is None


def test_extract_jsonl_skips_records_without_chat_content():
    text = "\n".join(
        [
            json.dumps({"kind": "other", "request": {"method": "GET"}}),
            json.dumps(
                {
                    "kind": "chat",
                    "request": {"messages": [{"role": "user", "content": "one"}]},
                    "response": {
                        "choices": [{"message": {"role": "assistant", "content": "two"}}]
                    },
                }
            ),
        ]
    )

    assert extract_jsonl_text(text) == "one\ntwo"


def test_extract_jsonl_reads_stored_exchange_responses():
    text = json.dumps(
        {
            "kind": "chat",
            "request": {"messages": [{"role": "user", "content": "one two"}]},
            "response": stored_chat_response("three"),
        }
    )

    assert extract_jsonl_text(text) == "one two\nthree"


def test_extract_jsonl_reports_bad_line():
    with pytest.raises(TokenInputError, match="line 2"):
        extract_jsonl_text('{"messages": []}\nnot json')


def test_estimate_upload_uses_chat_extraction_for_json():
    payload = {"messages": [{"role": "user", "content": "one two"}]}
    data = json.dumps(payload).encode()

    estimate = estimate_upload(
        data,
        "chat.json",
        encoding="utf-8",
        raw=False,
        counter=FakeTokenCounter(),
        smart_zone=10,
    )

    assert estimate.mode == "chat"
    assert estimate.tokens == 2
    assert estimate.characters == len(data.decode())
    assert estimate.lines == 1
    assert estimate.size_bytes == len(data)
    assert estimate.smart_zone_percent == 20
    assert estimate.warning is None


def test_estimate_upload_raw_ignores_json_extraction():
    payload = {"messages": [{"role": "user", "content": "one two"}]}
    data = json.dumps(payload).encode()

    estimate = estimate_upload(
        data,
        "chat.json",
        encoding="utf-8",
        raw=True,
        counter=FakeTokenCounter(),
        smart_zone=10,
    )

    assert estimate.mode == "raw"
    assert estimate.tokens == len(data.decode().split())


def test_estimate_upload_reports_invalid_json():
    with pytest.raises(TokenInputError, match="invalid JSON"):
        estimate_upload(
            b"{not json",
            "bad.json",
            encoding="utf-8",
            raw=False,
            counter=FakeTokenCounter(),
            smart_zone=10,
        )

    estimate = estimate_upload(
        b"{not json",
        "bad.json",
        encoding="utf-8",
        raw=True,
        counter=FakeTokenCounter(),
        smart_zone=10,
    )
    assert estimate.mode == "raw"


def test_estimate_upload_warns_for_unknown_extension():
    estimate = estimate_upload(
        b"hello",
        "data.bin",
        encoding="utf-8",
        raw=False,
        counter=FakeTokenCounter(),
        smart_zone=10,
    )

    assert estimate.mode == "raw"
    assert estimate.warning is not None
    assert "unknown extension" in estimate.warning


def test_estimate_upload_handles_jsonl():
    text = "\n".join(
        [
            json.dumps({"messages": [{"role": "user", "content": "one two"}]}),
            json.dumps({"messages": [{"role": "assistant", "content": "three"}]}),
        ]
    )

    estimate = estimate_upload(
        text.encode(),
        "log.jsonl",
        encoding="utf-8",
        raw=False,
        counter=FakeTokenCounter(),
        smart_zone=10,
    )

    assert estimate.mode == "chat"
    assert estimate.tokens == 3


def test_decode_text_strips_utf8_bom():
    assert decode_text(b"\xef\xbb\xbfhello") == "hello"


def test_decode_text_uses_requested_encoding():
    assert decode_text("中文".encode("gb18030"), "gb18030") == "中文"


def test_decode_text_rejects_invalid_utf8():
    with pytest.raises(TokenInputError):
        decode_text("中文".encode("gb18030"))


def test_count_messages_counts_whole_context():
    messages = [
        {"role": "system", "content": "one two"},
        {"role": "user", "content": "three"},
    ]

    assert count_messages(messages, FakeTokenCounter()) == 3


async def test_token_endpoint_counts_markdown(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post(
            "/api/tokens?filename=note.md", content=b"# Title\n\nHello world"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["tokens"] == 4
    assert body["mode"] == "raw"
    assert body["characters"] == 20
    assert body["lines"] == 3
    assert body["bytes"] == 20
    assert body["smart_zone_tokens"] == 150000
    assert body["smart_zone_percent"] == 0
    assert body["warning"] is None


async def test_token_endpoint_warns_for_unknown_extension(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=data.bin", content=b"hello")

    assert response.status_code == 200
    assert "unknown extension" in response.json()["warning"]


async def test_token_endpoint_extracts_chat_json(config):
    payload = json.dumps(
        {
            "messages": [
                {"role": "user", "content": "one two"},
                {"role": "assistant", "content": "three"},
            ]
        }
    ).encode()
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=chat.json", content=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "chat"
    assert body["tokens"] == 3


async def test_token_endpoint_reads_stored_exchange_jsonl(config):
    payload = json.dumps(
        {
            "kind": "chat",
            "request": {"messages": [{"role": "user", "content": "one two"}]},
            "response": stored_chat_response("three"),
        }
    ).encode()
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=log.jsonl", content=payload)

    assert response.status_code == 200
    assert response.json()["tokens"] == 3


async def test_token_endpoint_raw_override(config):
    payload = json.dumps({"messages": [{"role": "user", "content": "one two"}]}).encode()
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=chat.json&raw=1", content=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "raw"
    assert body["tokens"] > 2


async def test_token_endpoint_rejects_bad_json(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=bad.json", content=b"{not json")

    assert response.status_code == 422
    assert "invalid JSON" in response.json()["error"]


async def test_token_endpoint_accepts_bad_json_in_raw_mode(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post(
            "/api/tokens?filename=bad.json&raw=1", content=b"{not json"
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "raw"


async def test_token_endpoint_honours_encoding(config):
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post(
            "/api/tokens?filename=note.txt&encoding=gb18030",
            content="中文".encode("gb18030"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["characters"] == 2
    assert body["tokens"] == 1


async def test_token_endpoint_reports_tokenizer_failure(config):
    app = build_app(config, _no_upstream, token_counter=BrokenTokenCounter())
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=note.txt", content=b"hello")

    assert response.status_code == 503
    assert "offline" in response.json()["error"]


async def test_token_endpoint_reports_oserror(config):
    app = build_app(
        config, _no_upstream, token_counter=BrokenTokenCounter(OSError("disk full"))
    )
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=note.txt", content=b"hello")

    assert response.status_code == 503
    assert "disk full" in response.json()["error"]


async def test_token_endpoint_rejects_oversized_upload(config, monkeypatch):
    import dsserver.app as app_module

    monkeypatch.setattr(app_module, "MAX_UPLOAD_BYTES", 4)
    app = build_app(config, _no_upstream)
    async with client_for(app) as client:
        response = await client.post("/api/tokens?filename=note.txt", content=b"hello")

    assert response.status_code == 413
