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
