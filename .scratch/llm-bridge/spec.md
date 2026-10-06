# LLM Bridge — observe & save (v1)

Status: ready-for-agent

## Problem Statement

作为使用者，我一直用各种 OpenAI 兼容的聊天 app（当前主要是家里 Wi-Fi 上的一个手机 app）直连 DeepSeek。两件事困扰我：(1) 我看不到 app 在背后偷偷注入了什么 prompt（system 消息、人格、上下文）——而这恰恰是我作为 AI 工程师最想学的；(2) 我的聊天记录没有任何我能阅读、检索、保存的地方。我还希望将来能有个地方过滤和修改发给模型的内容，又不改动任何 app。

## Solution

一个本地自托管的 Python「Bridge」。任何 OpenAI 兼容 app 只需改它的 API base URL 指向 Bridge 即可。Bridge 把流量**逐字节原样**转发给 DeepSeek；对聊天请求，它把每次 Exchange（完整请求 + 重建后的响应 + 用量）记入 append-only 的 JSONL 真相日志，并渲染成人可读的 Markdown 会话文件，其中**明确区分 app 注入(system) 与我本人输入(user)**。不改任何 app、不用云服务器、除模型 API 外零成本。

## User Stories

1. 作为使用者，我只改 app 的 base URL 就能把任意 OpenAI 兼容 app 指向 Bridge，从而无需改动任何 app。
2. 作为使用者，我希望 Bridge 原样转发请求给 DeepSeek，从而用 Bridge 永远不会把 app 弄坏。
3. 作为使用者，我希望非聊天端点（如模型列表）原样透传，从而 app 的所有功能照常可用。
4. 作为使用者，我希望错误响应（4xx/5xx）带原始状态码/头/body 透传，从而 app 看到的是真实错误。
5. 作为使用者，我希望流式响应实时转发同时被记录，从而聊天手感正常且内容不丢。
6. 作为使用者，我希望每次 Exchange 存成一行 JSON、含完整请求与重建响应，从而不丢数据且可回放。
7. 作为使用者，我希望可选保存原始 SSE 文本，从而即使解析器有 bug 真相也不丢。
8. 作为使用者，我希望原始 `Authorization` 头永远不落库，从而我的 API key 从不被持久化。
9. 作为使用者，我希望只保存白名单请求头，从而能识别 Client 身份又不泄露密钥。
10. 作为使用者，我希望在 DeepSeek 提供时就记录 token 用量、且不引入额外机制，从而能看到花费。
11. 作为使用者，我希望每个会话一个 Markdown 文件，从而能把一来一回当一个文档读。
12. 作为使用者，我希望 app 注入的(system)消息与人类输入在排版上明确区分，从而能研究注入的 prompt。
13. 作为使用者，我希望有 reasoning/thinking 内容时一并展示，从而能从中学习。
14. 作为使用者，我希望有 Markdown 索引页，从而能快速找到会话。
15. 作为使用者，我希望 Markdown 可从 JSONL 重建，从而渲染逻辑变更后阅读视图能重算。
16. 作为使用者，我希望上游地址、监听地址、端口、深度路径、存储目录、原始SSE开关都在一个配置文件中，从而无需改代码即可调整行为。
17. 作为使用者，我希望 Bridge 跑在我的电脑上、同一 Wi-Fi 的手机能访问，从而能在手机上用。
18. 作为使用者，我希望它能开机自启，从而重启电脑后手机不会连不上。
19. 作为使用者，我希望将来能通过 Tailscale 在外网访问、且不改代码，从而实现远程使用。
20. 作为使用者，我希望数据模型从第一天就带 owner 字段，从而将来转多用户成本很低。
21. 作为使用者，我希望写入是串行的，从而并发请求不会把日志写坏。
22. 作为使用者，我希望单进程运行，从而不需要跨进程锁。
23. 作为使用者，我希望只存聊天请求的 body、非聊天请求只记元数据，从而大的/二进制载荷不会撑爆日志。
24. 作为使用者，我希望编辑/重新生成造成的分叉会话另起新文件，而不是冒险错误合并，从而分组永不弄错。
25. 作为使用者，我希望按稳定的会话前缀分组，从而重复重发完整历史的请求能归并进同一文件。
26. 作为使用者，我希望这版为将来的过滤/修改留好接缝，即使它现在不在范围内。

## Implementation Decisions

- **形态**：Bridge = 透明反向代理（见 ADR-0001）。非聊天端点与错误响应逐字节透传；不改写流式响应。
- **协议**：以 OpenAI 兼容的 `POST /chat/completions` 为一等协议；Upstream 默认 `https://api.deepseek.com`。
- **鉴权**：纯透传 Client 的 `Authorization`；Bridge 不持有 key；Bridge 自身无登录，绑 `0.0.0.0:<port>`（config 可改），默认端口 8787。
- **深度处理判定**：方法=POST 且路径 ∈ `deep_paths` 且响应 2xx → 解析并完整落库；否则透传。
- **流式**：tee —— 边收边原样转发，同时累积，结束后落库。
- **持久化**：append-only JSONL 为唯一真相；一行一个 Exchange。字段形状（决策密集，来自设计阶段）：
  ```json
  {
    "id": "uuid", "owner": "local", "ts": "ISO-8601", "kind": "chat",
    "client": { "user_agent": "...", "headers": { "...白名单..." } },
    "request": { "method": "POST", "path": "...", "model": "...",
                 "stream": true, "messages": [ "完整原文" ],
                 "tools": [ "..." ], "params": { "其余顶层参数" } },
    "response": { "status": 200, "usage": { "..." },
                  "finish_reason": "stop",
                  "message": { "role": "assistant", "content": "...",
                               "reasoning_content": "...", "tool_calls": [ "..." ] } },
    "raw_sse": "仅当 keep_raw_sse=true",
    "meta": { "latency_ms": 1234, "upstream": "api.deepseek.com" }
  }
  ```
- **用量**：非流式读响应 `usage`；流式读 `[DONE]` 前最后一个 chunk 的 `usage`（DeepSeek 必带）。**不做本地分词**。
- **请求头**：只存白名单（如 `User-Agent`、`X-Title` 等）；永不存 `Authorization`；不存 IP。
- **非聊天请求**：只记 `kind` + 方法/路径/状态码/耗时元数据，不存 body。
- **会话分组**：会话键 = `hash(system 消息 + 首条 user 消息)`；凡消息数组以已知前缀**延伸**的请求，只把 delta（新增消息 + 助手回复）追加进该会话；**分叉**（编辑/重生成）则另起新会话文件（`-b2`…）。
- **Markdown**：每会话一文件，命名 `{YYYY-MM-DD}-{slug}`（slug 取首条 user 消息前几词、清洗为安全字符，中文/空则回退短哈希）；渲染 delta；分块标注「注入(system) / 人类(user) / 助手(assistant)」；展示模型、tokens、耗时、reasoning；另生成 `index.md`。
- **重建**：提供 `render` 命令从 JSONL 重算全部 Markdown；正常写入时也增量追加。
- **配置**：`upstream_base_url`、`bind`、`port`、`deep_paths`、`store_dir`、`keep_raw_sse`。
- **并发**：单进程（uvicorn 不加 `--workers`）；一把 asyncio 锁串行化写入；每条记录一次性写完整行并 flush。
- **栈**：Python 3.11+、FastAPI、Uvicorn、httpx(async)、uv。
- **模块（按职责）**：配置加载、HTTP 入口/路由、通用透传、聊天解析、SSE tee、JSONL 存储、Markdown 分组与渲染、Exchange 数据结构。
- **未来多用户**：每条记录带 `owner`，当前恒为 `local`。

## Testing Decisions

- **好测试的定义**：只驱动 app 的 HTTP 接口，断言 (a) 返回给 Client 的字节、(b) 落盘文件；绝不断言内部函数或实现细节。
- **唯一接缝（seam）**：Bridge 的 HTTP 接口（HTTP boundary）。外部 Upstream 换成一个可控假上游（`httpx.MockTransport` 或本地 stub，地址经 config 注入）。全代码库就这一个接缝。
- **测试类型**：HTTP 层集成测试（integration testing at the HTTP boundary），不做针对单个函数的单元测试。
- **经该接缝覆盖的行为**：非聊天逐字节透传；错误透传；非流式聊天落库含 usage；流式聊天边转发边累积、usage 取自末块；落库记录不含 `Authorization`；请求头白名单；深路径判定；会话分组（延伸 vs 分叉）；Markdown 能标出注入消息；`render` 能从 JSONL 复现 Markdown。
- **模块**：上述行为横跨透传、聊天解析、流式、存储、Markdown，全部从这一接缝进入。
- **先例**：全新仓库，无先例；本 spec 建立模式——httpx ASGI 测试客户端 + 临时 store 目录 + 假上游。

## Out of Scope

- 过滤 / 修改请求或响应（优先级 2）。
- 自动 prompt 学习 / few-shot 抽取 / 微调（优先级 3）。
- Web UI。
- 多用户账号与鉴权。
- SQLite（推迟到过滤/检索阶段作索引）。
- Docker。
- HTTPS/Caddy 本地证书、Tailscale 本身的具体搭建。
- 存储非聊天请求的 body。
- 响应侧实时改写。

## Further Notes

- 架构选择记录于 `docs/adr/0001-transparent-reverse-proxy.md`。
- DeepSeek 在最后一个流式 chunk 自动带 `usage`；支持 `reasoning_content`、`tool_calls`、thinking 模式。
- 手机 app 可能拒绝明文 `http://`；届时用 Caddy 本地证书兜底，已列入范围外。
- 领域术语以 `GLOSSARY.md` 为准：Bridge、Client、Upstream、Exchange、Injected Prompt。
