# 会话命名 + 渲染性能 + EPUB 管线 + 统一 GUI

Status: ready-for-agent

## Problem Statement

作为使用者，我用 Bridge 把聊天记录存进 `exchanges.jsonl` 并渲染成 Markdown 阅读。三个问题困扰我：

1. **文件名不能改。** 会话文件名是从首条 user 消息派生的（`{日期}-{slug}`），我想给它起个有意义的名字以便查找，但它是导出结果，改了下次渲染就被覆盖。
2. **渲染越来越重。** 每收到一条聊天消息，Bridge 就把**全部**会话 Markdown 重写一遍。所有文件的时间戳被同时刷新（分不清哪些是真正变化的），且开销随历史增长而膨胀。
3. **阅读管线割裂。** 我有一套跨设备流程——电脑/手机下载 epub → 在电脑上转换成我的电纸书能流畅渲染的 epub；以及把 `data/` 里的 Markdown 会话选出来、编辑、打包成 epub 下发到电纸书。目前这只是 `epub/working_by_ds.py` 这个批处理脚本，没有统一的入口。

## Solution

在 Bridge 上增加一层统一的 Web GUI（纯静态 HTML + fetch，与后端同源），并把后端按模块重组：

- **会话命名**：用户可在 GUI 里给会话改名。名称作为一条 Record 持久化进 `exchanges.jsonl`（唯一事实源），作为该会话的 Markdown 文件名。渲染永不再覆盖用户起的名字。聊天流量只追加日志；改名时只重建受影响的单个文件与索引。
- **EPUB 管线**：把 `working_by_ds.py` 的转换能力封装为服务模块，提供两种动作——(a) 转换一个已存在的 epub；(b) 把选中的会话打包成一个新 epub。输入与产物统一收在 `data/epub/` 下。
- **统一 GUI**：会话列表 / 改名 / 选择 / 编辑副本 / 打包 epub / 上传或扫描 epub / 转换，全部在同一个页面里完成。

## User Stories

1. 作为使用者，我希望在 GUI 里给会话起一个有意义的名字，从而能一眼认出它。
2. 作为使用者，我希望我起的名字保存在唯一事实源里，从而重建 Markdown 不会把它弄丢。
3. 作为使用者，我希望重命名是一个明确的操作（而非我直接去改磁盘文件），从而系统总知道会话对应哪个文件。
4. 作为使用者，我希望改名后立刻看到文件名更新，从而不用手动跑渲染命令。
5. 作为使用者，我希望改名只重建那一个文件，从而不会因为改一个名字就重写整个目录。
6. 作为使用者，我希望每条新聊天消息只重建它所属的会话文件，从而渲染开销不随历史总量增长。
7. 作为使用者，我希望内容没变的 Markdown 文件不被重写，从而文件时间戳只反映真实修改。
8. 作为使用者，我希望开始服务时从日志重建内存索引，从而重启后一切照常、无需额外持久状态。
9. 作为使用者，我希望索引是一份可从日志重算的缓存，从而它永远不是第二个事实源。
10. 作为使用者，我希望 GUI 里列出所有会话，从而能浏览、搜索、选择。
11. 作为使用者，我希望会话列表显示日期、名称、轮数，从而能快速判断内容。
12. 作为使用者，我希望在 GUI 里勾选若干会话，从而能把它们打包成一本 epub。
13. 作为使用者，我希望把选中的会话生成一份可编辑的副本，从而能在不影响原始会话的前提下修改内容。
14. 作为使用者，我希望在"编辑"和"打包"之间可以停留、多次编辑，从而能反复打磨再导出。
15. 作为使用者，我希望编辑副本与源会话彻底脱钩，从而编辑它绝不会回写 `exchanges.jsonl` 或 `conversations/`。
16. 作为使用者，我希望打包完成后可以丢弃编辑副本，从而不留下无用状态。
17. 作为使用者，我希望转换一个已存在的 epub（电纸书兼容处理），从而能从电脑或手机拿到成品。
18. 作为使用者，我希望把 epub 从电脑直接拖进 `data/epub/inbox/`，从而无需上传也能处理。
19. 作为使用者，我希望也能把 epub 从手机发送到服务，从而在手机上就能投递。
20. 作为使用者，我希望服务能扫描 `data/epub/inbox/`，从而能一键处理 inbox 里所有 epub。
21. 作为使用者，我希望转换/打包的成品落在 `data/epub/out/`，从而输入输出分离、便于取用。
22. 作为使用者，我希望这一切都在同一个页面、同一个服务进程里，从而不用同时运维多个工具。
23. 作为使用者，我希望 GUI 不引入 node/npm 构建链，从而维持纯 Python 栈、部署简单。
24. 作为使用者，我希望它能在局域网/Tailscale 上访问，从而手机也能用同一个界面。
25. 作为使用者，我希望会话 Markdown 的渲染规则本身不变，从而阅读视图与今天一致。
26. 作为使用者，我希望 EPUB 内容尽量不依赖外部工具（如 pandoc），从而部署时少一个运行时依赖。
27. 作为使用者，我希望日志的 Record 种类被设计成"事件"而非"状态"，从而将来若要压缩日志可以安全丢弃过时记录。
28. 作为使用者，我希望改名、打包等操作有明确的错误反馈（如名字冲突、文件不存在），从而能自己纠正。

## Implementation Decisions

- **两个独立的事实源，互不隶属**：
  - Conversation 的事实源 = `exchanges.jsonl`（append-only）。派生视图 = `conversations/*.md`、`index.md`，均可重建。
  - EPUB 管线的事实源 = `data/epub/` 下的工作副本与输入物。派生产物 = `data/epub/out/`。
  - 一个副本从会话生成的那一刻起就"迁移"到 EPUB 事实源，与 Conversation 不再有关系。
- **Record 扩展**：日志新增 `kind:"rename"` 记录，形状为 `{kind:"rename", key, name, ts}`，`key` 为会话身份（`hash(system + 首条 user)`）。渲染时套用改名（按 `ts` 后写胜出）作为文件名覆盖。其余 Record 种类（`chat`/`other`）不变。
- **Record 是事件不是状态**：rename 表示"发生过一次改名"，而非"当前名字"。因此将来压缩日志可安全丢弃被后续记录覆盖的旧 rename。
- **会话身份 = (key, 分支)**：key 由请求头两条消息算出；分支由"消息前缀精确匹配"决定（保持现状，`signatures[:len(history)] == candidate.history`）。已知脆弱点：客户端若裁剪历史或改写 system 消息会导致误分新分支——本版接受，不加固（见 Out of Scope）。
- **内存索引**：服务启动时重放日志构建 `key → [分支列表]`（结构同现有 `states`），随后不再是"每消息重放全日志"，而是增量更新。索引是缓存，可随时从日志重建，不是事实源。
- **渲染时机**：聊天消息只追加日志；渲染降级为：(a) 启动时全量重建；(b) CLI `render` 全量重建；(c) 改名时只重建受影响的单文件 + `index.md`。收到聊天消息**不再**在请求路径上同步全量渲染。
- **增量写出**：渲染器对每个目标文件先渲染成字符串，与现有内容比对，相同则跳过写入（修掉"所有文件时间戳被同时刷新"的问题）。
- **改名是应用事件**：通过 GUI/API 显式发起，系统据此改磁盘文件名 + 更新索引。不监听文件系统、不靠文件名反推身份。
- **API 契约（在现有 HTTP 边界上新增）**：
  - `GET /` → 返回 GUI 页面（静态 HTML，内嵌原生 JS）。
  - `GET /api/conversations` → 列出会话（含 key、name、date、turns）。
  - `POST /api/conversations/{key}/rename` → `{name}`，改名。
  - `POST /api/epub/convert` → 转换 inbox 中的 epub（或上传的 epub）。
  - `POST /api/epub/work` → 由选中的会话生成可编辑副本。
  - `GET/PUT /api/epub/work/{id}` → 读取/保存副本内容。
  - `POST /api/epub/build` → 由副本（或选中会话）打包成 epub。
  - `GET /api/epub/files` → 列出 inbox/out 中的文件。
- **EPUB 模块**：把 `working_by_ds.py` 现有的干净库函数（`unpack_epub`/`convert_styles`/`repack_epub`/`process_folder`）封装为服务模块；剥离其 `__main__` 批处理路径。Markdown→EPUB 由**纯 Python 实现**（组装 XHTML/OPF/NCX），不依赖 pandoc。
- **目录结构**：
  ```
  data/
    exchanges.jsonl      ← 事实源
    conversations/*.md    ← 派生视图
    index.md              ← 派生视图
    epub/
      inbox/              ← 输入（拖入/上传/扫描）
      work/               ← 编辑副本（EPUB 管线的工作草稿，可丢弃）
      out/                ← 成品（可丢弃）
  ```
- **GUI 技术形态**：静态 HTML + fetch，无前端构建链，与后端同源，单进程服务。
- **模块（按职责）**：配置、HTTP 入口/路由、透传、聊天解析、SSE tee、日志存储、会话分组与 Markdown 渲染（含内存索引与改名套用）、EPUB 转换模块、Markdown→EPUB 构建模块、Web/GUI 层。

## Testing Decisions

- **好测试的定义**：只驱动 app 的 HTTP 接口，断言 (a) 返回给 Client 的响应、(b) `exchanges.jsonl` 内容、(c) `data/` 下落盘的产物。绝不断言内部函数或实现细节。
- **唯一接缝（seam）**：沿用现有 HTTP 边界（`tests/conftest.py` 的假 Client via `ASGITransport` + 假 Upstream via `MockTransport`）。本特性不新增接缝。
- **EPUB 内容断言**：经由 HTTP 触发后，用 `zipfile` 对外层 zip 断言（`mimetype` 首条且 STORED、存在 `container.xml`/OPF/目标 XHTML），不调内部转换函数。
- **经该接缝覆盖的行为**：
  - 改名后：日志新增一条 `rename` 记录；`conversations/` 下出现新文件名；`index.md` 更新。
  - 重建后：改名仍生效（日志重放保留用户名字）。
  - 增量：新聊天消息到达后，未变化的 `.md` 文件内容/时间戳不变。
  - `GET /api/conversations` 反映改名。
  - 建副本后编辑副本内容不会改动 `exchanges.jsonl` 与 `conversations/*.md`。
  - 打包产出合法 EPUB。
  - 转换产出合法 EPUB。
  - 扫描 inbox 能处理放入的 epub。
- **模块**：上述行为横跨日志存储、渲染/索引、EPUB 转换、EPUB 构建、Web 层，全部从这一接缝进入。
- **先例**：沿用 `.scratch/llm-bridge/spec.md` 建立的模式（httpx ASGI 测试客户端 + 临时 store 目录 + 假上游）。

## Out of Scope

- 日志压缩 / 轮转（`exchanges.jsonl` 的 compaction）。本版只把 Record 设计成事件式以留出空间；不实现。
- 加固分支匹配（滑动窗口裁剪、system 改写导致的误分叉）。接受现状，记为已知脆弱点。
- 在 GUI 里回写/编辑**原始**会话内容（编辑只发生在 EPUB 工作副本，绝不回写事实源）。
- 独立前端框架（React/Vue）与 node 构建链。
- 多用户账号与鉴权。
- Docker、HTTPS/Caddy、Tailscale 本身的具体搭建。
- 手机端"如何发送 epub 到服务"的最终形态（先留 API 接缝，细节另议）。
- pandoc 或其它外部电子书工具。

## Further Notes

- 决策记录于 `docs/adr/0002-log-is-the-single-source-of-truth.md`。
- 领域术语以 `GLOSSARY.md` 为准：Record、Facts Store、Conversation、Conversation Name、Rendered View、EPUB Pipeline。
- 会话身份 = (key, 分支)：`key` 不在磁盘任何地方，是重放时算出的推导值；rename 记录靠它跨重建稳定定位会话。
- 原始性能问题的根因是"每消息全量重渲染 + 全量重写"；本 spec 的渲染时机调整与增量写出共同修复它。
