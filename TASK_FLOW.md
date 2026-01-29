# 任务运行流程与技术文档

本文档详细描述了 Browser Cluster 系统的任务处理生命周期、参数配置、异常处理机制及缓存策略。

## 1. 任务运行全流程

任务的生命周期从 API 调用开始，到结果存储或缓存返回结束。

### 1.1 任务提交阶段 (API 层)
1. **请求接收**：API 接收到抓取请求（同步 `/scrape`、异步 `/scrape/async` 或批量 `/scrape/batch`）。
2. **参数校验**：使用 Pydantic 模型对 URL、抓取参数（`params`）和缓存配置（`cache`）进行自动校验和补全。
3. **缓存检查**：
   - 如果启用了缓存且是同步请求，系统根据 `url` + `params` 生成唯一的 `cache_key`。
   - 检查 Redis 中是否存在有效缓存。如果命中，直接返回结果并向 MongoDB 插入一条状态为 `success` 且 `cached: true` 的记录。
4. **数据库持久化**：如果未命中缓存或为异步请求，在 MongoDB `tasks` 集合中创建一个初始状态为 `pending` 的任务记录。
5. **消息入队**：将任务信息推送到 RabbitMQ 队列中。

### 1.2 任务分发阶段 (Queue 层)
1. **负载均衡**：RabbitMQ 根据 `prefetch_count` 设置，将任务分发给空闲的 Worker 节点。
2. **状态更新**：Worker 接收到任务后，立即将数据库中的任务状态更新为 `processing`，并记录当前的 `node_id`。

### 1.3 任务执行阶段 (Worker 层)
1. **浏览器分配**：Worker 调用 `BrowserManager` 获取 Playwright 浏览器实例（每个线程维护独立的连接）。
2. **环境准备**：
   - 设置视口大小（`viewport`）。
   - 注入反检测脚本（`stealth` 模式）。
   - 设置资源拦截规则（如拦截图片、媒体）。
   - 设置 API 拦截监听器（`intercept_apis`）。
3. **页面导航**：执行 `page.goto(url)`，并根据配置的等待策略（`wait_for`）和超时时间（`timeout`）等待页面加载。
4. **内容提取**：获取渲染后的 HTML、页面标题、状态码，并根据需要执行截图操作。
5. **资源清理**：任务完成后关闭 Page 对象，释放资源。

### 1.4 结果归档阶段
1. **成功处理**：
   - 更新数据库状态为 `success`。
   - 存储 HTML、截图和元数据。
   - 如果启用了缓存，将结果写入 Redis，设置相应的过期时间（TTL）。
2. **失败处理**：
   - 捕获异常，记录错误消息和堆栈。
   - 更新数据库状态为 `failed`。

---

## 2. 抓取参数说明 (ScrapeParams)

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `wait_for` | string | `networkidle` | 等待策略：`networkidle` (网络空闲), `load` (加载完成), `domcontentloaded` |
| `wait_time` | int | `3000` | 页面加载后的额外等待时间（毫秒），用于处理动态渲染 |
| `timeout` | int | `30000` | 整体超时时间（毫秒） |
| `selector` | string | `null` | 等待特定的 CSS 选择器出现后再返回 |
| `screenshot` | bool | `false` | 是否需要截图 |
| `is_fullscreen` | bool | `false` | 是否截取整页（长图） |
| `block_images` | bool | `false` | 是否拦截图片资源（可显著提高抓取速度） |
| `block_media` | bool | `false` | 是否拦截视频、音频、字体、CSS 等资源（可显著提高抓取速度） |
| `user_agent` | string | `null` | 自定义浏览器 User-Agent |
| `viewport` | dict | `{"width": 1920, "height": 1080}` | 模拟的浏览器视口大小 |
| `proxy` | dict | `null` | 代理服务器配置，格式：`{"server": "...", "username": "...", "password": "..."}` |
| `stealth` | bool | `true` | 是否启用反检测插件，模拟真实人类行为 |
| `intercept_apis` | list | `[]` | 要拦截并提取数据的接口 URL 模式列表（支持正则） |
| `intercept_continue`| bool | `false` | 拦截接口后是否继续执行请求（默认 False 为中止请求） |

---

## 3. 异常处理机制

系统针对各种不稳定因素设计了多层防护：

### 3.1 正常异常 (业务类)
- **页面加载超时**：如果页面在 `timeout` 内未达到 `wait_for` 状态，系统会检查当前已加载的内容。如果已获取到部分 HTML，会尝试降级返回；否则标记为 `failed`。
- **选择器未找到**：如果配置了 `selector` 但超时未出现，任务会继续执行并返回当前页面内容，但在日志中记录警告。

### 3.2 节点/环境异常 (系统类)
- **浏览器崩溃**：Worker 会捕获 Playwright 的连接错误，并尝试重新初始化浏览器实例。
- **消息队列断连**：RabbitMQ 消费者具备自动重连机制，确保节点在网络波动后能恢复工作。
- **并发冲突**：使用 `threading.local()` 隔离不同线程的浏览器上下文和数据库连接，避免跨线程资源竞争导致的 `IndexError` 或 `AttributeError`。

### 3.3 任务重试
- 用户可以通过 API 或管理后台触发 **Retry** 操作。
- 重试会重置 `status` 为 `pending`，清除之前的 `error` 和 `result`，并将 `cached` 设为 `False` 强制重新抓取。

---

## 4. 缓存逻辑说明

- **缓存键 (Cache Key)**：由 `URL` + `排序后的 ScrapeParams` 组成，确保参数稍有变动即视为不同任务。
- **命中策略**：
  - `cached: true` 表示直接从 Redis 获取的结果。
  - `cached: false` 表示经过了实际的浏览器渲染过程。
- **生命周期 (TTL)**：默认缓存 1 小时，可通过请求参数中的 `cache.ttl` 自行定义。
