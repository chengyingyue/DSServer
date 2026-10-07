# DSServer 部署指南（中文）

DSServer 是一个本地自托管的 **桥接器（Bridge）**，位于 OpenAI 兼容客户端与
DeepSeek（上游 / Upstream）之间。它按字节原样转发流量，把每次
**交换（Exchange）** 追加写入 JSONL 日志，并渲染成清晰区分「注入提示词」与
「人类输入」的 Markdown 会话记录。内置的网页界面还能给会话命名，并为电纸书运行
一套 EPUB 管线。

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
port = 8787
deep_paths = ["/chat/completions", "/v1/chat/completions"]
store_dir = "data"
keep_raw_sse = true
```

| 字段 | 说明 |
| --- | --- |
| `upstream_base_url` | 上游 LLM 提供方地址，目前为 DeepSeek |
| `bind` | 监听地址；`0.0.0.0` 表示允许局域网访问 |
| `port` | 监听端口，默认 8787 |
| `deep_paths` | 需要拦截并记录的上游路径 |
| `store_dir` | 数据存储目录，默认 `data` |
| `keep_raw_sse` | 是否保留流式响应的原始 SSE |

> API Key 由客户端自带并原样透传，桥接器**从不存储**密钥。

## 4. 启动

```powershell
uv run dsserver
```

启动后，把客户端的 API Base URL 指向桥接器，例如：

- `http://192.168.1.50:8787`
- 或 `http://192.168.1.50:8787/v1`

### 后台运行（无需一直开着终端）

如果不想一直开着终端窗口，可以把它作为隐藏进程启动，并把日志输出到文件：

```powershell
Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run", "dsserver" `
  -RedirectStandardOutput "dsserver.log" -RedirectStandardError "dsserver.err.log"
```

查看是否在运行，以及需要时停止：

```powershell
Get-Process -Name dsserver
Stop-Process -Name dsserver
```

## 5. 网页界面（会话命名与 EPUB 管线）

用浏览器打开 `http://<主机>:8787/`。同一个页面可以：

- **浏览与命名会话**：所有会话都会列出，给任意一个起个名字，它就成为该会话
  Markdown 文件的文件名。名字作为一条 Record 存进日志，**重建或重启后依然保留**，
  渲染永远不会把它覆盖。
- **转换 EPUB**：把 EPUB 拖进 `data/epub/inbox/`，或直接上传，转换成适合电纸书的
  版本，产物落在 `data/epub/out/`。
- **由会话打包 EPUB**：勾选若干会话，得到一本包含其内容的 EPUB。
- **编辑工作副本**：由选中的会话生成一份可编辑副本，可反复编辑，再由它打包
  EPUB，用完后丢弃。编辑副本**绝不会**改动日志或渲染出的会话文件。

命名与打包只重写必须重写的内容：日志始终是唯一事实源，磁盘上的一切都是派生、
可重建的。

## 6. 重建阅读视图（Markdown）

Markdown 由 JSONL 日志派生，可随时重新生成：

```powershell
uv run dsserver render
```

## 7. 数据位置

- `data/exchanges.jsonl` — 只追加的真相日志，每行一次交换（也存放会话改名 Record）
- `data/conversations/*.md` — Markdown 阅读视图
- `data/index.md` — 会话列表
- `data/epub/inbox/` — 待转换的 EPUB（拖入或上传）
- `data/epub/work/` — 可编辑工作副本（归 EPUB 管线管理）
- `data/epub/out/` — 转换 / 打包产出的 EPUB

## 8. 家庭局域网部署

1. **固定局域网 IP** — 在路由器中为该电脑保留 DHCP 租约，或分配静态 IP，
   使客户端 Base URL 不会变化。
2. **Windows 防火墙** — 允许专用网络入站 TCP 8787：

   ```powershell
   New-NetFirewallRule -DisplayName "DSServer" -Direction Inbound -Protocol TCP -LocalPort 8787 -Action Allow -Profile Private
   ```

3. **登录自启动** — 在 `shell:startup` 中创建指向 `uv run dsserver`
   （工作目录 = 本仓库）的快捷方式，或用「任务计划程序」注册。

## 9. 日后远程访问

如需在家中以外使用，把桥接器放到免费的
[Tailscale](https://tailscale.com/) 网络之后即可，**无需改动任何代码或配置**。
详细配置步骤见 `Tailscale 配置指南.md`。

## 10. 常见验证清单

- [ ] `uv sync` 成功，`.venv` 已生成
- [ ] `uv run dsserver` 正常监听 8787 端口
- [ ] 同一 Wi-Fi 下的手机 App，Base URL 指向桥接器后可正常对话
- [ ] 真实手机使用后，`data/` 下出现记录并能渲染为 Markdown
- [ ] 浏览器打开 `http://<主机>:8787/` 能看到会话列表并改名
- [ ] `data/epub/inbox/` 中的 EPUB 能转换为 `data/epub/out/` 的成品
