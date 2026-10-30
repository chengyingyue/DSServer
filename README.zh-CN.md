# DSServer 部署指南（中文）

DSServer 是一个本地自托管的 **桥接器（Bridge）**，位于 OpenAI 兼容客户端与
DeepSeek（上游 / Upstream）之间。它按字节原样转发流量，把每次
**交换（Exchange）** 追加写入 JSONL 日志，并渲染成清晰区分「注入提示词」与
「人类输入」的 Markdown 会话记录。内置的网页界面还能给会话命名、估算文件 token，
并为电纸书运行一套 EPUB 管线。

> 本文件覆盖**部署、运行与网页界面**。项目概览见 `README.md`，领域词汇见 `GLOSSARY.md`。

## 1. 环境要求

- Python 3.11+（由 `uv` 自动管理）
- [uv](https://docs.astral.sh/uv/)

## 2. 首次部署

```powershell
# 进入项目目录
Set-Location C:\Users\wsadb\Documents\workspace\DSServer

# 安装依赖（创建 .venv 并按 uv.lock 固定版本）
uv sync
```

## 3. 配置

编辑根目录的 `config.toml`：

```toml
upstream_base_url = "https://api.deepseek.com"
bind = "0.0.0.0"            # 监听局域网；仅本机使用改为 127.0.0.1
port = 8787                # 生产端口
test_port = 8788           # 测试端口（配合 --env test 使用）
smart_zone_tokens = 150000 # 用于 token 显示的上下文预算
deep_paths = ["/chat/completions", "/v1/chat/completions"]
store_dir = "data"
keep_raw_sse = true
```

| 字段 | 说明 |
| --- | --- |
| `upstream_base_url` | 上游 LLM 提供方地址，目前为 DeepSeek |
| `bind` | 监听地址；`0.0.0.0` 表示允许局域网访问 |
| `port` | 生产端口，默认 8787 |
| `test_port` | 测试端口，默认 8788；与生产端口二选一启动 |
| `smart_zone_tokens` | 「智能区」上下文预算，用于 token 占比显示，默认 150000 |
| `deep_paths` | 需要拦截并记录的上游路径 |
| `store_dir` | 数据存储目录，默认 `data` |
| `keep_raw_sse` | 是否保留流式响应的原始 SSE |

> API Key 由客户端自带并原样透传，桥接器**从不存储**密钥。

## 4. 启动

```powershell
uv run dsserver
```

默认监听**生产端口**（`port`，8787）。若想改到**测试端口**（`test_port`，8788）——
用于不想干扰真实流量的试验——加 `--env test`：

```powershell
uv run dsserver serve --env test
```

一次只监听一个端口，两种模式行为完全一致。

启动后，把客户端的 API Base URL 指向桥接器，例如：

- `http://192.168.5.7:8787`
- 或 `http://192.168.5.7:8787/v1`

### 只保存会话、不调用模型

`POST /save`（也支持 `POST /save/chat/completions`）接收与聊天请求相同的请求体，
但桥接器**只记录、不转发上游**。它会在助手位置返回「用户最新一条消息 + `saved`，
以及估算的上下文 token 数」，因此这次保存会像普通模型回复一样出现——并出现在渲染出的
Markdown 里：

```
### Human (user)
最后一轮输入

### Assistant
最后一轮输入
saved · 1,234 tokens
```

token 数覆盖请求中所有消息内容，是内容估算；上游的聊天模板会带来少量额外开销，
权威数字仍是 API 返回的 `usage`。若 tokenizer 无法加载，回复就只有 `saved`。
若请求带 `stream: true`，桥接器会返回 SSE 流（`text/event-stream`，以
`data: [DONE]` 结尾），与上游一致，因此流式客户端无需改动。

### 后台运行（无需一直开着终端）

用 detached 启动器启动；它会立即返回，日志写入 `dsserver-<env>.log` /
`dsserver-<env>.err.log`：

```powershell
uv run python scripts/restart.py --env test
```

`--env test` 使用 `test_port`（8788）；`--env prod` 使用 `port`（8787）。加
`--restart` 会替换该端口上已有的进程；加 `--wait` 会等到页面可访问再返回。用
`--stop --env test`、`--stop --env prod` 或 `--stop --env all` 停止一个或两个服务
（例如在 `uv sync` 之前）。

测试服务器与生产共用 `data/`；只把它用于只读检查，写入类测试请用 pytest 的临时目录。

查看是否在运行，以及需要时停止：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8788/
Get-Process -Name dsserver
Stop-Process -Name dsserver
```

不要再用 `Start-Process` + 重定向 + `Start-Sleep`，它会让调用它的 shell 卡住。

## 5. 网页界面（会话命名与 EPUB 管线）

用浏览器打开 `http://<主机>:8787/`。同一个页面可以：

- **浏览与命名会话**：所有会话都会列出，给任意一个起个名字，它就成为该会话
  Markdown 文件的文件名。名字作为一条 Record 存进日志，**重建或重启后依然保留**，
  渲染永远不会把它覆盖。派生的文件名会保留中文等非 ASCII 字符，因此依然可读。
- **预览会话**：点击会话名（或它的 View 按钮），即可在页面内直接查看它的渲染内容，
  无需打开文件。
- **估算文件 token**：拖入或上传 `.md`、`.txt`、`.json` 或 `.jsonl` 文件（也可粘贴
  文本），估算其 token 数及占 `smart_zone_tokens` 的比例。JSON/JSONL 默认提取聊天
  内容；勾选 `Raw text` 可按原始文本计数。未知扩展名会按原始文本计数并给出警告；
  非 UTF-8 文件可在 **Encoding** 输入框中指定编码。
- **转换 EPUB**：把 EPUB 拖进 `data/epub/inbox/`，或直接上传，转换成适合电纸书的
  版本，产物落在 `data/epub/out/`。
- **由会话打包 EPUB**：勾选若干会话，得到一本包含其内容的 EPUB。
- **编辑工作副本**：由选中的会话生成一份可编辑副本，可反复编辑，再由它打包
  EPUB，用完后丢弃。编辑副本**绝不会**改动日志或渲染出的会话文件。
- **下载成品**：`data/epub/out/` 里的每个 EPUB，以及任意工作副本，都可以直接在
  页面上点击下载。

命名与打包只重写必须重写的内容：日志始终是唯一事实源，磁盘上的一切都是派生、
可重建的。

## 6. 重建阅读视图（Markdown）

Markdown 由 JSONL 日志派生，可随时重新生成：

```powershell
uv run dsserver render
```

## 7. 一眼看清 token 用量

每个渲染出的会话，开头会显示**最新一轮**的上下文规模，并与 `smart_zone_tokens`
对比：

```
**Prompt token:  74,000 prompt (49% of 150k)**
> 最新一轮上下文已用 49% 的 smart zone。
Total token: 89,000
```

当 prompt 达到预算的 80% 时，会出现 `⚠️` 警告。每个 Turn 标题仍会显示它自己的
`N total tokens · N ms`。同样的数字会在每笔交换落库时打印到服务端控制台。

### 估算文件 token

网页界面的 **Tokens** 区块可以估算 `.md`、`.txt`、`.json` 或 `.jsonl` 文件（或粘贴
文本）的 DeepSeek token 数，并显示字符数、行数、字节数以及占 `smart_zone_tokens`
的百分比。

- `.md` / `.txt` 按原文计数。
- `.json` / `.jsonl` 默认提取聊天内容：`messages`、`request.messages` 以及助手回复
  内容；没有聊天内容的记录会被跳过。勾选 **Raw text** 可按整个文件的原文计数。
- 未知扩展名会按原始文本计数并给出警告；非 UTF-8 文件可在 **Encoding** 输入框中
  指定编码。
- 首次使用会从 DeepSeek 官方下载离线 tokenizer（约 6 MB）到
  `data/tokenizers/deepseek_v4/`，之后复用。计数完全在本机完成，文件内容不会离开本机。
- 结果只估算消息内容；上游的聊天模板会带来少量额外开销，权威数字仍是 API 返回的
  `usage`。

## 8. 数据位置

- `data/exchanges.jsonl` — 只追加的真相日志，每行一次交换（也存放会话改名 Record）
- `data/exchanges.jsonl.cache.pkl` — 派生的解析缓存，用于加快启动；可随时删除，下次启动会重建（ADR 0006）
- `data/conversations/*.md` — Markdown 阅读视图
- `data/index.md` — 会话列表
- `data/epub/inbox/` — 待转换的 EPUB（拖入或上传）
- `data/epub/work/` — 可编辑工作副本（归 EPUB 管线管理）
- `data/epub/out/` — 转换 / 打包产出的 EPUB
- `data/tokenizers/` — 缓存的 DeepSeek tokenizer（首次使用时下载）

## 9. 家庭局域网部署

1. **固定局域网 IP** — 在路由器中为该电脑保留 DHCP 租约，或分配静态 IP，
   使客户端 Base URL 不会变化。
2. **Windows 防火墙** — 允许专用网络入站 TCP 8787：

   ```powershell
   New-NetFirewallRule -DisplayName "DSServer" -Direction Inbound -Protocol TCP -LocalPort 8787 -Action Allow -Profile Private
   ```

3. **登录自启动** — 在 `shell:startup` 中创建指向 `uv run dsserver`
   （工作目录 = 本仓库）的快捷方式，或用「任务计划程序」注册。

## 10. 日后远程访问

如需在家中以外使用，把桥接器放到免费的
[Tailscale](https://tailscale.com/) 网络之后即可，**无需改动任何代码或配置**。
详细配置步骤见 `Tailscale 配置指南.md`。

## 11. 常见验证清单

- [ ] `uv sync` 成功，`.venv` 已生成
- [ ] `uv run dsserver` 正常监听 8787 端口
- [ ] `uv run dsserver serve --env test` 正常监听 8788 端口
- [ ] `POST /save` 在助手位置返回「最新用户输入 + `saved · N tokens`」，且不转发上游、出现在 Markdown 中
- [ ] 网页界面的 Tokens 区块能估算上传的 Markdown、文本、JSON 或 JSONL 文件
- [ ] 渲染出的会话顶部显示最新一轮的 `Prompt token` / `Total token` 与占比
- [ ] 同一 Wi-Fi 下的手机 App，Base URL 指向桥接器后可正常对话
- [ ] 真实手机使用后，`data/` 下出现记录并能渲染为 Markdown
- [ ] 浏览器打开 `http://<主机>:8787/` 能看到会话列表并改名
- [ ] `data/epub/inbox/` 中的 EPUB 能转换为 `data/epub/out/` 的成品
