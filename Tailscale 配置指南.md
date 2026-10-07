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

假设你的 uv server 监听在 `127.0.0.1:8787`。服务本身只需绑定本地回环地址，不用改成 `0.0.0.0`，Tailscale 会负责转发。

### 2. 开启 Tailscale Serve

打开命令提示符（CMD）或 PowerShell，运行：

```bash
tailscale serve --bg http://127.0.0.1:8787
```

> 把 `8787` 换成你实际的服务端口。

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

### 手机端连不上
- 确认手机 Tailscale 处于“已连接”状态。
- 确认 base URL 填的是 `https://...ts.net`，没有多余端口号。
- 如果之前挂过 VPN，先关掉再试，避免路由冲突。
- 电脑上运行 `tailscale serve status` 确认代理规则还在。

### 长连接（SSE/WebSocket）问题
部分框架需要额外配置 `trusted proxy` 或允许特定 Origin，否则连接建立后可能很快断开。如果遇到，检查 uv server 的反向代理信任设置。

---

## 五、日常使用

- **电脑端**：Tailscale 保持运行，Serve 规则是持久的，重启后会自动生效（`--bg` 参数）。
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