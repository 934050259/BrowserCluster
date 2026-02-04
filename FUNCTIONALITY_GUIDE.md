# Browser Cluster 功能说明文档

## 项目概述

**Browser Cluster** 是一个高性能、分布式的浏览器自动化集群系统，基于 Playwright 和 FastAPI 构建。它支持大规模并发网页抓取、截图、PDF 生成及自动化操作，具备完善的任务调度、结果缓存和节点管理功能。

### 核心技术栈

- **后端框架**: Python 3.10 + FastAPI
- **浏览器引擎**: Playwright (Chromium/Firefox/WebKit)
- **消息队列**: RabbitMQ
- **数据库**: MongoDB (数据存储) + Redis (缓存/队列)
- **前端框架**: Vue 3 + Element Plus + Pinia + Vite

---

## 一、网页采集功能

### 1.1 基础抓取功能

系统提供三种抓取模式，满足不同场景需求：

#### 同步抓取 (`POST /api/v1/scrape/`)
- **功能**: 提交任务后同步等待结果返回
- **适用场景**: 需要立即获取结果的场景
- **特点**:
  - 自动检查 Redis 缓存，命中则直接返回缓存结果
  - 支持超时轮询等待，默认30秒
  - 返回完整的 HTML、元数据、截图（可选）等结果

#### 异步抓取 (`POST /api/v1/scrape/async`)
- **功能**: 提交任务后立即返回任务ID，后台异步执行
- **适用场景**: 耗时较长的任务、批量任务、无需即时响应的场景
- **特点**:
  - 立即返回 task_id，不等待执行结果
  - 可通过任务查询接口获取结果
  - 适合高并发场景

#### 批量抓取 (`POST /api/v1/scrape/batch`)
- **功能**: 一次性提交多个抓取任务
- **适用场景**: 批量采集多个页面
- **特点**:
  - 支持多个任务并行提交
  - 返回多个 task_id
  - 每个任务可配置不同的参数

### 1.2 高级采集参数

抓取请求支持丰富的配置参数：

#### 等待策略
- **wait_for**: 页面加载等待策略
  - `networkidle`: 网络空闲时返回（默认）
  - `load`: 页面加载完成时返回
  - `domcontentloaded`: DOM 加载完成时返回
- **wait_time**: 额外等待时间（毫秒），用于处理动态渲染内容
- **timeout**: 总超时时间（毫秒），默认30000ms
- **selector**: 等待特定 CSS 选择器出现后再返回

#### 页面渲染控制
- **screenshot**: 是否生成页面截图（Base64格式）
- **is_fullscreen**: 是否截取全屏（长图）
- **viewport**: 自定义浏览器视口大小，默认 1920x1080
- **user_agent**: 自定义 User-Agent
- **block_images**: 拦截图片资源加载（显著提升速度）
- **block_media**: 拦截视频、音频、字体、CSS等资源

#### 反检测功能
- **stealth**: 启用反检测插件，模拟真实人类行为（默认开启）

#### 认证与会话
- **cookies**: 注入 Cookie，支持多种格式
  - 字符串格式: `"name=value; session=123"`
  - JSON 对象格式: `{"name": "value", "session": "123"}`
  - JSON 数组格式: `[{"name": "value", "domain": ".example.com"}]`
  - 自动适配主域名，支持跨域共享

### 1.3 代理支持

支持通过代理服务器访问目标网站，适用于：
- 访问海外网站
- 匿名访问
- 绕过地域限制

**配置方式**:
```json
{
  "proxy": {
    "server": "http://proxy.example.com:8080",
    "username": "username",  // 可选
    "password": "password"   // 可选
  }
}
```

**支持的代理类型**:
- HTTP 代理: `http://proxy.example.com:8080`
- HTTPS 代理: `https://proxy.example.com:8443`
- SOCKS5 代理: `socks5://proxy.example.com:1080`

### 1.4 API 拦截功能

支持在页面渲染过程中拦截并提取特定 XHR/Fetch 接口数据。

**配置方式**:
```json
{
  "intercept_apis": [
    "https://api.example.com/*",
    "*/api/v1/data/*",
    "https://example.com/api/products"
  ],
  "intercept_continue": false
}
```

**特性**:
- 支持通配符 `*` 进行 URL 模式匹配
- 拦截的接口数据包含：URL、请求方法、状态码、响应头、响应体
- JSON 响应自动解析为对象
- `intercept_continue`: true 时继续请求，false 时中止请求（默认）

**返回数据结构**:
```json
{
  "result": {
    "html": "<html>...</html>",
    "intercepted_apis": {
      "https://api.example.com/*": [
        {
          "url": "https://api.example.com/users",
          "method": "GET",
          "status": 200,
          "headers": {...},
          "body": {...}
        }
      ]
    }
  }
}
```

### 1.5 缓存功能

基于 Redis 的高效缓存机制：

- **缓存键**: 由 URL + 抓取参数生成唯一键
- **TTL**: 支持自定义过期时间，默认3600秒（1小时）
- **缓存策略**:
  - 同步抓取优先检查缓存
  - 异步抓取可配置是否启用缓存
  - 缓存命中时在数据库中记录 `cached: true`
- **管理**:
  - 支持通过 API 手动清除指定缓存
  - 自动过期清理

---

## 二、数据解析功能

系统支持三种解析模式，适配不同复杂度的网页：

### 2.1 智能通用解析 (GNE)

**功能**: 基于正文抽取算法，自动提取新闻类网站的标题、正文及发布时间

**特点**:
- 零配置，开箱即用
- 自动识别正文区域
- 提取标题、作者、发布时间等元数据
- 适用于新闻、博客、资讯类网站

**使用方式**:
```json
{
  "parser": "gne"
}
```

**返回数据示例**:
```json
{
  "title": "文章标题",
  "content": "正文内容...",
  "author": "作者",
  "publish_time": "2024-01-01 10:00:00",
  "images": [...]
}
```

### 2.2 精准规则解析 (XPath/CSS)

**功能**: 通过可视化配置 XPath 或 CSS 选择器，实现像素级精准数据提取

**特点**:
- 精准定位 DOM 元素
- 支持多字段映射
- 适合电商、列表页等结构化页面
- 支持正则后处理

**使用方式**:
```json
{
  "parser": "xpath",
  "parser_config": {
    "rules": {
      "title": "//h1[@class='product-title']/text()",
      "price": "//span[@class='price']/text()",
      "description": "//div[@class='desc']//text()"
    }
  }
}
```

### 2.3 大模型智能解析 (LLM)

**功能**: 结合 OpenAI/DeepSeek 等大语言模型，通过自然语言描述实现复杂网页的语义化提取

**特点**:
- 零代码，通过自然语言描述提取需求
- 智能理解页面语义
- 支持复杂结构化数据提取
- 需要配置 LLM API Key

**使用方式**:
```json
{
  "parser": "llm",
  "parser_config": {
    "fields": ["title", "price", "description", "rating"]
  }
}
```

**系统配置**:
- LLM API Key
- LLM API Base URL
- LLM Model Name

---

## 三、API 接口功能

### 3.1 抓取接口

#### `POST /api/v1/scrape/`
同步抓取网页

**请求参数**:
```json
{
  "url": "https://example.com",
  "params": {
    "wait_for": "networkidle",
    "wait_time": 3000,
    "timeout": 30000,
    "screenshot": true,
    "block_images": true,
    "proxy": {...},
    "intercept_apis": [...],
    "parser": "gne"
  },
  "cache": {
    "enabled": true,
    "ttl": 3600
  },
  "priority": 1
}
```

**响应示例**:
```json
{
  "task_id": "65b2...",
  "url": "https://example.com",
  "status": "success",
  "result": {
    "html": "<!DOCTYPE html>...",
    "metadata": {
      "title": "页面标题",
      "load_time": 2.34,
      "timestamp": "2024-01-01T00:00:00Z"
    },
    "screenshot": "data:image/png;base64,..."
  },
  "cached": false
}
```

#### `POST /api/v1/scrape/async`
异步抓取网页

**请求参数**: 与同步抓取相同

**响应示例**:
```json
{
  "task_id": "65b2...",
  "url": "https://example.com",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### `POST /api/v1/scrape/batch`
批量抓取网页

**请求参数**:
```json
{
  "tasks": [
    {
      "url": "https://example.com/1",
      "params": {...},
      "priority": 1
    },
    {
      "url": "https://example.com/2",
      "params": {...},
      "priority": 2
    }
  ]
}
```

**响应示例**:
```json
{
  "task_ids": ["65b2...", "65b3..."]
}
```

### 3.2 任务管理接口

#### `GET /api/v1/tasks/{task_id}`
获取单个任务详情

**查询参数**:
- `include_html`: 是否包含完整 HTML 源码（默认true）
- `include_screenshot`: 是否包含截图数据（默认true）

**响应**: 完整的任务信息，包括 HTML、截图、错误堆栈等

#### `GET /api/v1/tasks`
获取任务列表（分页）

**查询参数**:
- `status`: 任务状态过滤
- `url`: URL 模糊搜索
- `cached`: 是否命中缓存
- `skip`: 跳过记录数
- `limit`: 返回记录数

**响应示例**:
```json
{
  "total": 100,
  "tasks": [
    {
      "task_id": "65b2...",
      "url": "https://example.com",
      "status": "success",
      "cached": false,
      "duration": 2.34,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/tasks/{task_id}/retry`
重试失败的任务

- 重置任务状态为 pending
- 清除之前的错误和结果
- 重新提交到队列

#### `DELETE /api/v1/tasks/{task_id}`
删除单个任务

#### `DELETE /api/v1/tasks/batch`
批量删除任务

### 3.3 统计接口

#### `GET /api/v1/stats`
获取系统统计数据

**响应示例**:
```json
{
  "today": {
    "total": 100,
    "success": 95,
    "failed": 5,
    "avg_duration": 2.5
  },
  "queue": {
    "pending": 10,
    "processing": 3
  },
  "nodes": {
    "total": 3,
    "active": 2,
    "inactive": 1
  }
}
```

### 3.4 定时任务接口 (Schedules)

#### `POST /api/v1/schedules`
创建定时任务。支持两种调度策略：
- **Interval**: 每隔固定秒数执行。
- **Cron**: 使用标准 Crontab 表达式。

**请求参数**:
```json
{
  "name": "每日抓取示例",
  "url": "https://example.com",
  "schedule_type": "cron",
  "cron": "0 0 * * *",
  "params": {
    "screenshot": true
  }
}
```

#### `GET /api/v1/schedules`
分页获取所有定时任务。支持按名称模糊搜索和按状态过滤。

#### `POST /api/v1/schedules/{id}/toggle`
一键激活或暂停定时任务。

#### `POST /api/v1/schedules/{id}/run`
立即手动执行一次任务，不影响原有的调度计划。

---

## 四、管理界面功能

### 4.1 首页/仪表盘 (Home)

**功能**:
- 系统概览展示
- 核心特性介绍
- 快速入口导航
- 架构流程可视化

**展示内容**:
- 任务总数、成功数、失败数
- 队列堆积情况
- 节点在线状态
- 核心指标统计

### 4.2 任务管理 (Tasks)

**功能**:
- 任务列表展示（支持分页）
- 任务创建（单个/批量）
- 任务详情查看
- 任务结果预览
- 任务重试
- 任务删除（单个/批量）

**任务操作**:
- 查看详情：查看完整的 HTML、截图、API 拦截数据等
- 重试：重新执行失败的任务
- 删除：删除任务记录
- 获取 API 配置：查看当前任务的 API 请求 JSON，方便集成到外部系统
- 复制任务 ID：快速复制任务 ID

### 4.3 定时任务 (Schedules)

**功能**:
- 定时任务列表展示：实时显示任务状态、最近运行时间和预计下一次运行时间。
- 定时任务创建/编辑/删除：支持配置完整的抓取参数（如 Cookie、代理、拦截规则等）。
- 调度策略配置：支持“间隔执行”和“Cron 表达式”两种模式。
- 任务状态控制：支持一键启用/禁用，禁用后任务将从调度器中移除。
- 手动立即执行：提供测试按钮，可立即触发一次抓取以验证配置。
- 历史执行记录追踪：点击“执行记录”可跳转至该任务产生的所有采集记录。

**调度策略**:
- **间隔执行 (Interval)**: 适用于高频抓取，如“每 1 分执行一次”。
- **Cron 表达式 (Cron)**: 适用于特定时间点抓取，如“每周一早上 8 点”。支持标准的 Crontab 语法。

### 4.4 节点管理 (Nodes)

**功能**:
- 节点列表展示
- 节点状态监控
- 节点启停控制
- 节点删除

### 4.4 网站配置 (Rules)

**功能**:
- 规则列表展示
- 规则创建/编辑/删除
- 规则测试
- 规则导入/导出

**规则配置**:
- **GNE 规则**: 无需配置，使用默认提取算法
- **XPath 规则**: 配置字段与 XPath 表达式映射
- **LLM 规则**: 配置需要提取的字段列表

### 4.5 系统配置 (Configs)

**功能**:
- 系统配置查看
- 配置修改
- 配置重置
- 系统日志查看
- 系统重启

### 4.6 用户管理 (Users)

**功能**:
- 用户列表展示
- 用户创建/编辑/删除
- 角色权限管理

**角色权限**:
- **管理员**:
  - 所有功能访问权限
  - 系统配置修改权限
  - 用户管理权限
  - 节点管理权限

- **普通用户**:
  - 任务创建和查询权限
  - 任务删除权限
  - 解析规则使用权限

### 4.7 统计分析 (Stats)

**功能**:
- 实时统计图表
- 历史趋势分析
- 性能指标监控

---

## 五、系统特性

### 5.1 分布式架构

- **多节点水平扩展**: 支持动态添加/删除 Worker 节点
- **任务优先级调度**: 基于优先级的任务队列，高优先级任务优先处理
- **负载均衡**: RabbitMQ 自动分发任务到空闲节点
- **高可用**: 节点故障自动恢复，消息持久化

### 5.2 高性能

- **浏览器池复用**: 减少浏览器启动开销
- **资源智能拦截**: 拦截图片、媒体等资源，显著提升渲染速度
- **Redis 缓存**: 热点数据缓存，重复请求秒级响应
- **异步处理**: 全链路异步，高并发支持

### 5.3 反检测能力

- **Stealth 模式**: 内置反检测插件，模拟真实人类行为
- **User-Agent 伪装**: 支持自定义 User-Agent
- **指纹模拟**: 模拟真实浏览器指纹
- **代理支持**: 支持代理池，隐藏真实 IP

### 5.4 多模式解析

- **GNE 通用解析**: 零配置自动提取新闻类网站内容
- **XPath/CSS 精准解析**: 可视化配置规则，像素级精准提取
- **LLM 智能解析**: 大模型语义理解，自然语言描述提取需求

### 5.5 监控与管理

- **实时监控**: 任务状态、节点状态、队列堆积实时监控
- **历史溯源**: 完整的任务历史记录，支持结果回溯
- **日志系统**: 详细的操作日志和错误日志
- **统计报表**: 丰富的统计图表，支持趋势分析

### 5.6 安全性

- **JWT 认证**: 基于 JWT 的用户认证
- **RBAC 权限**: 基于角色的访问控制
- **API 鉴权**: 所有 API 接口需要认证
- **敏感信息保护**: 日志中自动过滤敏感信息

---

## 六、部署指南

### 6.1 本地部署 (Local Deployment)

#### 1. 前置要求
- Python 3.10+
- Node.js 22+
- 已安装并运行的 RabbitMQ, MongoDB, Redis

#### 2. 克隆仓库
```bash
git clone https://github.com/934050259/BrowserCluster.git
cd browser-cluster
```

#### 3. 环境配置
复制 `.env.example` 并修改：
```bash
cp .env.example .env
```
配置数据库和消息队列连接信息：
```ini
MONGO_URI=mongodb://localhost:27017/
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

#### 4. 初始化
```bash
# 初始化配置
python scripts/init_configs_db.py
# 初始化管理员 (账号: admin, 密码: admin)
python scripts/init_admin.py
```

#### 5. 后端启动
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install chromium
uvicorn app.main:app --reload
```

#### 6. Worker 启动
```bash
python scripts/start_worker.py
```
或者在后台管理界面-节点管理内添加并启动worker

#### 7. 前端启动
```bash
cd admin
npm install
npm run dev
```

### 6.2 Docker 部署 (Docker Deployment)

### 1. 准备环境

构建镜像前，请确保已按完成以下准备工作：

1. **环境配置**：创建 `.env` 文件并配置好远程或宿主机的数据库连接信息。
2. **初始化数据库**：在宿主机运行初始化脚本（只需执行一次）：
   ```bash
   python scripts/init_configs_db.py
   python scripts/init_admin.py
   ```
#### 2. 构建镜像
在项目根目录下执行：
```bash
docker build -t browser-cluster:latest .
```

#### 2. 运行容器
```bash
docker run -d \
  --name browser-cluster \
  -p 8000:8000 \
  browser-cluster:latest
```
> 注意：环境变量需根据实际网络环境调整。

#### 4. 部署说明
- 镜像内置了前端编译后的静态资源，启动后可通过 `http://localhost:8000` 访问。
- Worker 节点可以通过后台管理界面的“节点管理”模块进行动态添加和启动。

---

## 七、任务处理流程 (详细)

### 7.1 同步抓取流程
```
1. 客户端发起请求
   ↓
2. API Gateway 接收请求，JWT 鉴权
   ↓
3. 检查 Redis 缓存
   ├─ 命中缓存 → 返回缓存结果 → 记录任务到数据库 → 完成
   └─ 未命中 → 继续
   ↓
4. 创建任务记录到 MongoDB（状态：pending）
   ↓
5. 发布任务到 RabbitMQ
   ↓
6. 轮询查询任务状态
   ↓
7. Worker 消费任务
   ↓
8. 启动浏览器上下文
   ↓
9. 执行页面渲染和数据提取
   ↓
10. 更新任务状态（success/failed）
   ↓
11. 写入结果到 MongoDB
   ↓
12. 如果启用缓存，写入 Redis
   ↓
13. 返回结果给客户端
```

### 6.2 异步抓取流程

```
1. 客户端发起请求
   ↓
2. API Gateway 接收请求，JWT 鉴权
   ↓
3. 创建任务记录到 MongoDB（状态：pending）
   ↓
4. 发布任务到 RabbitMQ
   ↓
5. 立即返回 task_id 给客户端
   ↓
6. Worker 消费任务
   ↓
7. 启动浏览器上下文
   ↓
8. 执行页面渲染和数据提取
   ↓
9. 更新任务状态（success/failed）
   ↓
10. 写入结果到 MongoDB
   ↓
11. 如果启用缓存，写入 Redis
   ↓
12. 客户端通过 task_id 查询结果
```

---

## 七、使用场景

### 7.1 SEO 数据采集

采集搜索引擎结果页面，提取排名、标题、描述等信息。

### 7.2 电商价格监控

监控电商平台商品价格变化，支持代理池和反检测。

### 7.3 新闻内容聚合

使用 GNE 解析器自动提取新闻网站正文内容。

### 7.4 社交媒体监控

采集社交媒体平台公开数据，支持 Cookie 认证。

### 7.5 API 数据提取

拦截页面加载过程中的 API 请求，直接获取结构化数据。

### 7.6 网站截图

批量生成网页截图，用于网站快照或监控。

### 7.7 大数据分析

结合 LLM 解析，实现复杂网页的语义化数据提取。

---

## 八、最佳实践

### 8.1 性能优化

1. **启用缓存**: 对重复访问的 URL 启用缓存
2. **拦截资源**: 根据需求拦截图片、媒体资源
3. **合理设置并发**: 根据服务器配置调整 Worker 并发数
4. **使用异步接口**: 批量任务使用异步接口提升吞吐量

### 8.2 反检测策略  

1. **开启 Stealth 模式**: 模拟真实浏览器行为
2. **使用代理池**: 轮换使用不同代理 IP
3. **随机 User-Agent**: 模拟不同浏览器
4. **控制请求频率**: 避免短时间内大量请求

### 8.3 错误处理

1. **设置合理超时**: 根据网站响应速度调整超时时间
2. **启用重试机制**: 对失败任务自动重试
3. **监控错误日志**: 定期查看错误日志，及时发现问题
4. **优雅降级**: 部分加载失败时返回已获取内容

---

## 九、故障排查

### 9.1 任务失败常见原因

1. **超时错误**: 检查 timeout 设置，适当增加超时时间
2. **选择器未找到**: 检查 selector 配置，或使用 wait_time 增加等待
3. **浏览器崩溃**: 检查服务器资源，增加内存或减少并发
4. **反爬虫拦截**: 启用 Stealth 模式，使用代理，降低请求频率

### 9.2 性能问题排查

1. **响应慢**: 检查是否启用了缓存，是否拦截了资源
2. **队列堆积**: 增加 Worker 节点，提高并发处理能力
3. **内存占用高**: 检查是否有长时间运行的浏览器，定期清理

### 9.3 日志查看

- **应用日志**: 通过管理后台-系统设置的"系统日志"功能查看
- **日志级别**: 可在配置中调整日志级别（DEBUG/INFO/WARNING/ERROR）

---
