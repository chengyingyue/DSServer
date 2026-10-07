from __future__ import annotations

from .conftest import build_app, chat_response, client_for, conversation_files, sequence_handler


async def test_repeated_history_is_grouped_into_one_conversation(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("6")]))
    request1 = {
        "model": "deepseek-flash",
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "What is 2+2?"},
        ],
    }
    request2 = {
        "model": "deepseek-flash",
        "messages": request1["messages"]
        + [{"role": "assistant", "content": "4"}, {"role": "user", "content": "And 3+3?"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request1)
        await client.post("/chat/completions", json=request2)

    files = conversation_files(config)
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    body = text.split("## Turn 1", 1)[1]
    assert body.count("What is 2+2?") == 1
    assert body.count("And 3+3?") == 1
    assert "## Turn 2" in body


async def test_injected_and_human_messages_are_labelled(config):
    app = build_app(config, sequence_handler([chat_response("4")]))
    request = {
        "model": "deepseek-flash",
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "What is 2+2?"},
        ],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request)

    text = conversation_files(config)[0].read_text(encoding="utf-8")
    body = text.split("## Turn 1", 1)[1]
    assert "### Injected (system)" in body
    assert "### Human (user)" in body
    assert "### Assistant" in body
    assert body.index("Be terse.") > body.index("### Injected (system)")
    assert body.index("What is 2+2?") > body.index("### Human (user)")


async def test_a_divergent_topic_starts_a_new_conversation(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("Blue")]))
    request1 = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
    }
    request2 = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "Favorite color?"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=request1)
        await client.post("/chat/completions", json=request2)

    assert len(conversation_files(config)) == 2


async def test_extension_after_a_fork_rejoins_the_original_conversation(config):
    app = build_app(
        config,
        sequence_handler([chat_response("4"), chat_response("5"), chat_response("6")]),
    )
    base_messages = [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    base = {"model": "deepseek-flash", "messages": base_messages}
    fork = {"model": "deepseek-flash", "messages": list(base_messages)}
    extended = {
        "model": "deepseek-flash",
        "messages": base_messages
        + [{"role": "assistant", "content": "4"}, {"role": "user", "content": "And 3+3?"}],
    }
    async with client_for(app) as client:
        await client.post("/chat/completions", json=base)
        await client.post("/chat/completions", json=fork)
        await client.post("/chat/completions", json=extended)

    files = conversation_files(config)
    assert len(files) == 2
    original = next(path for path in files if "-b2" not in path.name)
    assert "## Turn 2" in original.read_text(encoding="utf-8")


async def test_index_lists_all_conversations(config):
    app = build_app(config, sequence_handler([chat_response("4"), chat_response("Blue")]))
    async with client_for(app) as client:
        await client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Q1"}]})
        await client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Q2"}]})

    index = config.index_path.read_text(encoding="utf-8")
    for path in conversation_files(config):
        assert path.name in index


async def test_non_ascii_topic_keeps_a_readable_filename(config):
    app = build_app(config, sequence_handler([chat_response("你好")]))
    async with client_for(app) as client:
        await client.post("/chat/completions", json={"messages": [{"role": "user", "content": "你好世界"}]})

    files = conversation_files(config)
    assert len(files) == 1
    assert "你好世界" in files[0].name
