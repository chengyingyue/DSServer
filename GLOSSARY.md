# DSServer (LLM Bridge)

A personal Python server that sits between the AI app the owner actually uses and the LLM provider, so that all traffic can be observed, filtered, modified, and persisted — primarily so the owner can study how the app constructs its prompts.

## Language

**Bridge**（桥接器）:
The Python HTTP server that sits between the Client and the Upstream, intercepting their traffic to observe, filter, modify, and persist conversations.
_Avoid_: proxy, gateway, middleware；代理、网关、中间件

**Client**（客户端）:
Any OpenAI-compatible application the owner chooses to point at the Bridge. The Bridge is not built for one specific app; each Client is simply an OpenAI-format caller whose base URL has been redirected.
_Avoid_: app, frontend, UI；应用、前端、界面

**Upstream**（上游）:
The LLM provider API that ultimately serves model responses. Currently DeepSeek, in OpenAI-compatible mode.
_Avoid_: backend, AI server, model server；后端、模型服务

**Exchange**（交换）:
A single request sent by a Client and the Upstream response it produced. It is the unit the Bridge persists.
_Avoid_: transaction, call, round-trip；交易、调用、往返

**Injected Prompt**（注入提示词）:
The content the Client adds to a request before sending it (system messages, persona, retrieved context), as opposed to what the human types. The owner wants to read these to learn prompt engineering.
_Avoid_: system prompt, hidden prompt, boilerplate；系统提示词、隐藏提示词、模板

**Record**（记录）:
One line in the exchange log (`exchanges.jsonl`). A Record is one of several kinds; a chat Exchange is one kind, and a Conversation rename is another.
_Avoid_: entry, event, row；条目、事件

**Facts Store**（事实源 / 日志）:
The append-only `exchanges.jsonl`. It is the single source of truth: every rendered artifact is reconstructed from it and can be discarded and rebuilt. Nothing else may hold authoritative state.
_Avoid_: database, state file, source；数据库、状态文件

**Conversation**（会话）:
A chronological thread of Exchanges sharing one origin (system + first user message), together with the branching that grows from them. Derived from the Facts Store; never the source of truth.
_Avoid_: chat, thread, session；聊天、线程、会话记录

**Conversation Name**（会话名称）:
The human-readable label identifying a Conversation, shown as the filename of its rendered Markdown. Owned by the human and stored as a Record in the Facts Store — not inferred from message content once set.
_Avoid_: title, filename, slug；标题、文件名

**Conversation Identity**（会话标识）:
The pair of a Conversation's **key** and its **branch**, which together address exactly one Conversation. Used when a Conversation must be referenced unambiguously, such as when selecting Conversations to build or rename.
_Avoid_: id, address, ref；编号、地址

**Work Copy**（工作副本）:
An editable, disposable copy of one or more Conversations made for refinement before being packaged into an EPUB. Edits to a Work Copy never change the original Conversations or the Facts Store.
_Avoid_: draft, edit, snippet；草稿、编辑、片段

**Rendered View**（派生视图）:
Any `.md` file produced from the Facts Store — the per-Conversation files and the index. Disposable and rebuildable; their identity is the Conversation they render, not their filename.
_Avoid_: output, export, artifact；输出、导出、产物

**EPUB Pipeline**（EPUB 管线）:
The facility that turns reading material into ebooks tailored for the owner's e-reader — either by converting an existing EPUB, or by packaging selected Conversations into a new one.
_Avoid_: converter, exporter, builder；转换器、导出器
