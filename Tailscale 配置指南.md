# Tailscale 配置指南（手机访问电脑本地服务）
https://chat.deepseek.com/share/1pxebi8y4rdlge2iya
## 适用场景

用手机访问电脑上运行的本地服务（如 uv server、开发服务器等），无论在家还是在外都能用。Tailscale 会自动组网并解决 HTTPS 证书问题，绕开 Android 明文 HTTP 限制和局域网隔离。

---

## 一、准备工作

- 电脑和手机各安装 Tailscale
- 两端登录**同一个账号**（同一 tailnet）
- 国内网络环境安装/登录时，建议先挂代理（全局或 TUN 模式），登录成功后可以关掉

---

## 二、电脑端配置

### 1. 确认本地服务正常

假设你的 uv server 监听在 `127.0.0.1:8787`。绑定 `127.0.0.1` 或 `0.0.0.0` 都可以，Tailscale Serve 只转发到 `127.0.0.1:8787`。

### 2. 开启 Tailscale Serve

打开命令提示符（CMD）或 PowerShell，运行：

```bash
tailscale serve --bg http://127.0.0.1:8787
```

> 把 `8787` 换成你实际的服务端口。

**托盘进程必须保持运行。** Windows 版是客户端模式：最后一个 GUI 客户端（`tailscale-ipn.exe`）断开时，tailscaled 会自动断开 Tailscale，状态掉回 `NoState`。再执行一次 `tailscale up --unattended`，关闭托盘窗口或注销后仍保持在线。

**首次运行会提示开启 Serve 功能**，按终端输出的链接去浏览器登录并授权，然后重新运行上面的命令。

### 3. 获取 HTTPS 地址

命令成功后，终端会输出一个地址，格式类似：

```
https://<机器名>.<你的tailnet>.ts.net
```

这个就是手机端要填的 base URL。**不要加端口号**，Tailscale Serve 默认走 443 端口并自动提供 Let's Encrypt 证书。

### 4. 检查状态（可选）

```bash
tailscale serve status
```

会显示当前代理规则和对应的本地端口。

---

## 三、手机端配置

1. **安装 Tailscale**：从应用商店下载。
2. **登录同一账号**：确保和电脑在同一个 tailnet。
3. **开启连接**：打开 Tailscale App，保持开关为“已连接”状态。
4. **填入地址**：在你的手机 App 设置里，把 base URL 填成电脑上获取的那个 `https://...ts.net` 地址。

完成后，无论手机连 Wi-Fi 还是蜂窝数据，只要 Tailscale 开着，就能访问电脑上的服务。

---

## 四、常见问题

### 安装卡住
国内直连 Tailscale 服务器可能超时。挂代理（全局/TUN 模式）后重装即可。

### `tailscale` 不是内部或外部命令
用完整路径运行：

```bash
"C:\Program Files\Tailscale\tailscale.exe" serve --bg http://127.0.0.1:8787
```

### 提示 `Serve is not enabled on your tailnet`
按终端输出的链接去浏览器登录并授权开启 Serve，然后重新运行命令。

### 电脑端连不上（`NoState` / Serve 丢失）

先跑仓库里的自检，一条命令看全部状态：

```powershell
uv run python scripts/check_remote.py
```

再按症状对照：

| 症状 | 含义 | 处理 |
| --- | --- | --- |
| `BackendState=NoState`、`Tailscale is starting` | daemon 未连上；常见于托盘进程没开 | 启动 `C:\Program Files\Tailscale\tailscale-ipn.exe` |
| 日志有 `client disconnected (…): disconnecting Tailscale` | 最后一个 GUI 客户端退出，Tailscale 被断开 | 同上，并执行 `tailscale up --unattended` |
| `tailscale serve status` 输出 `No serve config` | Serve 规则丢失（daemon 卡死或状态重置） | 重新执行 `tailscale serve --bg http://127.0.0.1:8787` |
| `tailscale status` 显示 `Unable to connect to the Tailscale coordination server` | 网络到控制面不通 | 检查代理/VPN，再 `tailscale up` |
| 手机能连、本机 opencode 连不上 | 本机 Client 的 baseURL 指向 ts.net，而 Tailscale 已断 | 见上一行；或把本机 baseURL 改成 `http://127.0.0.1:8787` |

服务端日志在 `C:\ProgramData\Tailscale\Logs\tailscale-service-*.txt`。普通权限读不了，需要管理员复制出来看；最新的文件即当前进程。

### 手机端连不上
- 确认手机 Tailscale 处于“已连接”状态。
- 确认 base URL 填的是 `https://...ts.net`，没有多余端口号。
- 如果之前挂过 VPN，先关掉再试，避免路由冲突。
- 电脑上运行 `tailscale serve status` 确认代理规则还在。

### 长连接（SSE/WebSocket）问题
部分框架需要额外配置 `trusted proxy` 或允许特定 Origin，否则连接建立后可能很快断开。如果遇到，检查 uv server 的反向代理信任设置。

---

## 五、日常使用

- **电脑端**：Tailscale 保持运行（托盘进程 `tailscale-ipn.exe` 必须在跑），并执行一次 `tailscale up --unattended`，这样关闭托盘窗口或注销后仍然在线。Serve 规则通常重启后仍在，但 daemon 卡死或状态被重置后会丢失——重连后先跑 `tailscale serve status` 确认。
- **手机端**：每次使用时打开 Tailscale 开关即可。
- **关闭 Serve**（如果需要）：

```bash
tailscale serve off
```

---

## 核心优势

- 不需要找局域网 IP，不需要改服务监听地址
- 不需要开防火墙端口
- 自动提供 HTTPS，绕开 Android 明文限制
- 在家、在外都能用，不受网络环境变化影响