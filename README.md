# Browser Cluster

<p align="center">
  <strong>中文</strong> | <a href="README_EN.md">English</a>
</p>

> [!IMPORTANT]
> **前期项目会有较多 bug，请大家踊跃提 issues，作者看到后第一时间更新！**

<p align="center">
  <img src="admin/public/chat.png" width="200" alt="Author Image">
</p>

<p align="center">
  <strong>联系作者，欢迎加入项目交流群~</strong><br>
</p>

**Browser Cluster** 是一个高性能、分布式的浏览器自动化集群系统，基于 **Playwright** 和 **DrissionPage** 双浏览器引擎以及 FastAPI 构建。它支持大规模并发网页抓取、截图、解析及自动化操作，具备**内置智能代理池与账号 Cookie 池管理机制**，支持自动检测与频率控制，特别针对 Cloudflare 等高难度反爬网站进行了深度优化，提供完善的任务调度、结果缓存、节点监控及资源状态维护功能。

![UI Preview](admin/public/image.png)

## 🚀 核心特性

- **双浏览器引擎支持**：支持 Playwright 和 DrissionPage 双引擎切换。
    - **Playwright**：适用于复杂的自动化交互和 API 拦截场景。
    - **DrissionPage**：原生抗检测能力强，可轻松绕过 Cloudflare 5秒盾及各类人机验证。
- **分布式架构**：支持多 Worker 节点水平扩展，轻松应对高并发场景。
- **隐身与反检测**：
    - Playwright 内置 Stealth 插件。
    - DrissionPage 采用浏览器指纹抹除技术，支持 Linux 环境深度隐藏。
- **高效缓存**：基于 Redis 的结果缓存机制，支持自定义 TTL。
- **资源优化**：智能拦截图片、媒体资源，显著提升渲染速度。
- **API 拦截**：支持在渲染过程中提取特定 XHR/Fetch 接口数据。
- **OSS 云存储支持**：
    - 支持将抓取的 HTML 源码和页面截图自动上传至阿里云 OSS。
    - 解决大规模数据存储压力，支持私有桶安全访问。
    - 后端自动代理 OSS 内容，解决前端直接访问的跨域及权限问题。
- **智能代理池管理**：
    - 支持 HTTP/HTTPS/SOCKS5 等多种协议的代理接入。
    - 支持隧道代理与静态代理，内置自动认证逻辑。
    - **多级代理继承**：采集任务可自动继承解析规则中配置的代理池，简化配置流程。
    - **一键全量检测**：支持手动触发或定时自动检测代理可用性。
    - **状态自动维护**：根据检测结果自动熔断不可用代理，确保采集任务的高成功率。
- **智能账号/Cookie 池管理**：
    - **多账号管理**：支持针对不同域名存储多个账号的 Cookie。
    - **自动调度与轮询**：抓取任务可指定 Cookie 分组，系统自动实现账号轮询。
    - **频率控制 (Rate Limiting)**：内置基于 Redis 的频率限制，防止单个账号抓取过快导致封号。
    - **有效性自动检测**：定期自动检测 Cookie 有效性，失效后自动剔除或提醒。
    - **一键导入导出**：支持 JSON 格式批量导入导出 Cookie 数据。
- **高可用分布式 Worker**：
    - **自动重连机制**：Worker 具备 RabbitMQ 连接断开自动重连能力，有效应对网络波动。
    - **多实例负载均衡**：支持多个 Worker 实例同时运行，自动竞争处理任务队列。
- **自动化调度**：内置定时任务引擎，支持 Interval 和 Cron 表达式，实现周期性数据采集。
- **多模式解析提取**：集成多种结构化数据提取技术，适配不同复杂度的网页：
    - **智能通用解析 (GNE)**：基于正文抽取算法，支持两种提取模式：
        - **详情模式 (Detail)**：自动提取新闻类网站的标题、正文、发布时间及作者。
        - **列表模式 (List)**：自动识别并提取新闻列表页中的标题、链接及发布日期。
    - **精准规则解析 (XPath/CSS)**：支持可视化配置 XPath 和 CSS 选择器，针对电商、列表页等结构化页面实现像素级精准提取。
    - **AI 智能提取的优势**：
        - ✅ **零代码配置**：只需输入 URL，AI 自动分析页面结构并生成 XPath 规则。
        - ✅ **智能识别**：自动识别列表容器、标题、链接、时间等关键字段。
        - ✅ **全加载保障**：获取 HTML 时自动等待页面完全加载（支持自定义等待时间），确保分析内容完整。
        - ✅ **可视化校验**：生成的规则可立即在界面上进行实时校验和微调。
    - **大模型智能解析 (LLM)**：结合 OpenAI/DeepSeek 等大语言模型，通过自然语言描述所需字段，零代码实现复杂网页的语义化提取。
- **可视化管理**：提供基于 Vue 3 + Element Plus 的现代化管理后台。
    - **无感刷新体验**：针对任务管理与采集记录页面进行了深度缓存优化，支持在 `keep-alive` 模式下的数据自动刷新与同步。
    - **解析透明化**：采集记录详情实时显示匹配到的解析规则域名，清晰掌握每一条数据的来源逻辑。
- **可视化流程编排 (Workflow)**：
    - **零代码编排**：基于 Vue Flow 的可视化拖拽界面，通过连接节点构建复杂的 Web 自动化流程。
    - **双引擎兼容**：编排的流程可无缝切换 Playwright/DrissionPage 引擎执行。
    - **17+ 动作节点**：覆盖点击、输入、滚动、拖拽、上传、JS 执行、条件分支、循环、多标签/iFrame 切换等全场景。
    - **流程级定时任务**：支持为单个工作流配置独立的 Cron 或固定间隔调度，并在列表页实时显示下次运行时间。
    - **结果深度沉淀**：自动捕获节点截图（JPEG Base64 压缩存储）、提取变量数据，并提供详尽的步骤级日志。
## 🛠️ 技术栈

- **后端**：Python 3.10, FastAPI, Playwright, RabbitMQ, MongoDB, Redis
- **前端**：Vue 3, Element Plus, Pinia, Vite
- **部署**：Docker (Multi-stage build)

## 🏗️ 系统架构

![Architecture](admin/public/app.jpeg)

### 🔄 任务处理流程

![Architecture](admin/public/architecture.png)

1. **请求接入与校验 (Entry)**
   - `API Gateway` 接收 HTTP 请求，执行 **JWT 鉴权**与参数合法性校验。
   - `Task Scheduler` 定期触发预设任务，直接跳过网关鉴权进入分发流程。
   - 检查 **Redis 缓存**：若命中缓存且未过期，则直接返回结果，跳过后续步骤。

2. **任务持久化与分发 (Dispatch)**
   - API 生成全局唯一 `task_id`，并在 **MongoDB** 中初始化任务状态（pending）。
   - **智能路由与代理预选**：根据任务目标及配置，从**代理配置**中预选可用代理。
   - 将任务载荷发布至 **RabbitMQ** 优先级队列，实现流量削峰。
   - 同步接口进入等待状态，异步接口立即返回 `task_id`。

3. **智能调度与执行 (Execution)**
   - 闲置 `Worker` 节点监听队列，根据**任务优先级**竞争获取任务。
   - Worker 调用 **Browser Manager** 分配独立浏览器上下文：
     - **代理注入与健康检查**：动态注入加密代理、验证连通性，若代理失效则触发**自动重试/更换**。
     - **环境模拟**：注入 Stealth 脚本、配置模拟指纹与视口。
     - **资源拦截**：根据配置拦截图片/媒体，加速渲染。
     - **实时拦截**：注册 API 拦截监听器，捕获 XHR/Fetch 数据。

4. **多模式解析 (Parsing)**
   - 页面加载完成后（根据 `wait_for` 策略），Worker 获取渲染后的 DOM。
   - 根据 `parser` 配置执行解析引擎：
     - **GNE**：自动提取正文与元数据。
     - **XPath/CSS**：按规则执行精准提取。
     - **LLM**：调用大模型进行语义化字段映射。

5. **结果归档与反馈 (Feedback)**
   - **成功处理**：将 HTML、结构化数据、截图及性能指标写入 MongoDB。
   - **代理状态反馈**：根据执行结果实时反馈至代理池，触发代理**熔断或权重调整**。
   - **结果归档**：将结果同步至 Redis（带 TTL），加速后续相同请求。
   - **异常处理**：若执行失败，记录错误堆栈并触发**重试机制**（可选）。
   - **统计更新**：实时上报任务状态，更新 **Prometheus/Stats** 监控数据。

### 核心组件

- **🌐 API Gateway (FastAPI)**
  - 系统的统一入口，负责接收 HTTP 请求、参数校验和任务调度。
  - 集成 Redis 缓存层，对重复请求直接返回缓存结果，显著降低系统负载。
  - 提供完整的任务管理、节点监控和系统配置 API。

- **⏰ Task Scheduler (APScheduler)**
  - 内置高性能任务调度引擎，支持大规模定时任务并发。
  - 支持任务状态实时控制（启用/禁用）、手动即时触发和执行历史追踪。
  - 提供 Interval (间隔) 和 Cron (表达式) 两种灵活的调度策略。

- **📨 Message Queue (RabbitMQ)**
  - 异步任务总线，实现生产者（API）与消费者（Worker）的完全解耦。
  - 支持任务持久化、优先级队列和 ACK 确认机制，确保高并发下的任务可靠性。

- **🤖 Worker Nodes (Playwright & DrissionPage)**
  - 分布式执行单元，支持容器化部署和水平扩展。
  - 负责启动浏览器上下文，执行页面渲染、交互、截图和数据提取。
  - **双引擎驱动**：根据任务参数动态选择 Playwright 或 DrissionPage。
  - **单例模式优化**：浏览器实例常驻复用，通过标签页管理任务，极大降低资源开销和启动延迟。
  - 内置 **Stealth Mode** 和资源拦截策略，优化抓取成功率和速度。

- **💾 Data Storage**
  - **MongoDB**: 存储全量任务记录、抓取结果、节点状态、工作流配置及执行记录。
  - **Redis**: 用于热点数据缓存和分布式锁，提升系统响应速度。

- **🧩 Workflow Orchestrator (Vue Flow)**
  - 基于节点的可视化编辑器，支持拖拽创建复杂的自动化脚本。
  - **Recursive Executor**: 后端递归执行器，支持变量解析、条件分支跳转及循环逻辑。
  - **Snapshot System**: 自动捕获操作快照，并以 80% 质量 JPEG 压缩为 Base64 存储，在保证画质的同时极大节省数据库空间。

- **🖥️ Admin Dashboard (Vue 3)**
  - **统计监控**：实时展示任务成功率、处理时长及队列堆积情况。
  - **代理管理**：可视化维护代理池，支持即时检测与批量导入。
  - **任务管理**：全量任务历史溯源，支持结果预览及错误日志查看。
  - **节点管理**：监控集群 Worker 状态、负载情况及资源占用，支持节点上下线管理。
  - **解析规则**：可视化维护各网站的解析模板，支持在线测试规则有效性。
  - **配置管理**：动态调整浏览器并发数、超时时间及全局代理设置，支持一键初始化系统配置到数据库。
- **用户管理**：基于角色的访问控制 (RBAC)，保障系统安全。

## 📦 快速开始

### 前置要求

- Python 3.10
- Node.js 22 
- RabbitMQ, MongoDB, Redis

### 本地开发

1. **克隆仓库**
   ```bash
   git clone https://github.com/934050259/BrowserCluster.git
   cd browser-cluster
   ```

2. **环境配置**
   复制示例配置文件并根据实际环境修改：
   ```bash
   cp .env.example .env
   # Windows (PowerShell)
   # copy .env.example .env
   ```
   
   修改 `.env` 文件中的数据库和消息队列连接信息：
   ```ini
   MONGO_URI=mongodb://localhost:27017/
   REDIS_URL=redis://localhost:6379/0
   REDIS_CACHE_URL=redis://localhost:6379/1
   RABBITMQ_URL=amqp://guest:guest@localhost:5672/
   ```

3. **初始化配置与账号**
   运行初始化脚本，导入默认配置并创建初始管理员账号：
   ```bash
   # 初始化系统配置
   python scripts/init_configs_db.py

   # 初始化默认管理员账号 (账号: admin, 密码: admin)
   python scripts/init_admin.py
   ```

4. **后端设置**
   ```bash
   # 安装依赖
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   playwright install chromium

   # 启动 API 服务
   uvicorn app.main:app --reload
   ```

5. **Worker 启动**
   Worker 负责从消息队列接收并执行实际的网页抓取任务：
   ```bash
   # 启动 Worker 进程
   python scripts/start_worker.py
   ```
   或者在后台管理界面-节点管理内添加并启动worker

6. **前端设置**
   ```bash
   cd admin
   npm install
   npm run build  # 构建后由后端统一托管，或运行 npm run dev 进行开发
   ```

7. **访问系统**
   - 管理后台：`http://localhost:8000` (后端托管) 或 `http://localhost:5173` (Vite 开发模式)
   - API 文档：`http://localhost:8000/docs`

## 🐳 Docker 部署

本项目支持多阶段构建，镜像内已集成前端静态资源和后端服务。

### 1. 构建镜像

直接在项目根目录运行以下命令进行构建，无需提前配置 `.env`：

```powershell
docker build -t browser-cluster:latest .
```

### 2. 运行容器

在启动容器时通过环境变量传入配置参数。容器启动后会自动执行数据库和系统配置的初始化。

#### 启动 API 服务 (含管理后台)

如果您追求最快启动，可以直接运行以下命令（不挂载卷）：

```powershell
docker run -d `
  --name browser-cluster `
  -p 8000:8000 `
  -e MONGO_URI="mongodb://192.168.1.100:27017/" `
  -e REDIS_URL="redis://192.168.1.100:6379/0" `
  -e REDIS_CACHE_URL="redis://192.168.1.100:6379/1" `
  -e RABBITMQ_URL="amqp://guest:guest@192.168.1.100:5672/" `
  browser-cluster:latest
```

> **💡 关于 data 和 logs 目录：**
> - **如果不设置挂载**：系统依然可以正常运行。程序会自动在容器内部创建 `data`（存储配置和账号）和 `logs`（存储日志）文件夹。
> - **缺点**：当您删除容器并重新创建时，在 Web 界面修改的配置和新创建的用户会**丢失**（恢复到默认状态）。
> - **建议**：如果您是在生产环境运行，或者希望保留配置，建议加上目录挂载：`-v ${PWD}/data:/app/data -v ${PWD}/logs:/app/logs`。

## ⚙️ 配置说明

主要配置项（可通过 `.env` 或环境变量设置）：

### 1. 基础环境配置

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DEBUG` | `true` | 是否开启调试模式（输出详细日志） |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8000` | 服务监听端口 |
| `SECRET_KEY` | `your-secret-key` | 系统安全密钥（建议生产环境务必修改） |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB 连接地址 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 任务队列/状态连接地址 |
| `REDIS_CACHE_URL` | `redis://localhost:6379/1` | Redis 结果缓存连接地址 |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ 连接地址 |

### 2. 浏览器与执行配置

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `BROWSER_TYPE` | `chromium` | 默认浏览器类型 (目前仅支持 `chromium`) |
| `HEADLESS` | `true` | 是否开启无头模式 |
| `STEALTH_MODE` | `true` | 是否开启反爬虫隐身模式 |
| `DEFAULT_TIMEOUT` | `30000` | 默认任务超时时间（毫秒） |
| `WORKER_CONCURRENCY` | `3` | 单个 Worker 节点的并发任务数 |
| `NODE_ID` | `node-1` | 节点唯一标识 |

### 3. OSS 存储配置 (可选)

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OSS_ENABLED` | `false` | 是否启用 OSS 存储（开启后可将结果存至云端） |
| `OSS_ENDPOINT` | - | OSS 访问域名（如 `oss-cn-hangzhou.aliyuncs.com`） |
| `OSS_ACCESS_KEY_ID` | - | OSS AccessKey ID |
| `OSS_ACCESS_KEY_SECRET` | - | OSS AccessKey Secret |
| `OSS_BUCKET_NAME` | - | OSS Bucket 名称 |

### 4. LLM 大模型配置 (可选)

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `LLM_API_BASE` | `https://api.openai.com/v1` | 大模型 API 基础地址 |
| `LLM_API_KEY` | - | 大模型 API 密钥 |
| `LLM_MODEL` | `gpt-3.5-turbo` | 使用的模型名称 |

## 📝 任务参数说明

> **提交格式说明**：本系统所有采集接口（同步、异步、批量）均采用 **JSON** 格式提交。请求头必须包含 `Content-Type: application/json`，参数需放置在 HTTP 请求体（Body）中。
> 
> - **Python (requests)**: 使用 `json={...}` 传参。
> - **JavaScript (Axios)**: 直接传入对象 `axios.post(url, {...})`。

### 1. 抓取接口 (POST /api/v1/scrape/)

这是最核心的接口，支持同步抓取并返回渲染后的结果。

#### **请求体 (JSON)**

| 参数名 | 类型 | 必选 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `url` | string | 是 | - | 目标网页的完整 URL 地址 |
| `params` | object | 否 | `{}` | 详细的抓取配置参数（见下表） |
| `cache` | object | 否 | `{"enabled": true, "ttl": 3600}` | 缓存配置（见下表） |
| `priority` | int | 否 | `1` | 任务优先级，数字越大越优先处理 |

#### **cache 配置详解**

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `enabled` | bool | `true` | 是否启用缓存 |
| `ttl` | int | `3600` | 缓存过期时间（秒），默认 1 小时 |

#### **params 配置详解**

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `wait_for` | string | `networkidle` | 等待策略：`networkidle` (网络空闲), `load` (加载完成), `domcontentloaded` |
| `wait_time` | int | `3000` | 页面加载完成后的额外等待时间（毫秒），用于处理异步渲染 |
| `timeout` | int | `30000` | 抓取总超时时间（毫秒） |
| `selector` | string | `null` | 等待特定的 CSS 选择器出现后再返回结果 |
| `screenshot` | bool | `false` | 是否生成页面截图 |
| `is_fullscreen` | bool | `false` | 是否截取全屏（仅在 `screenshot` 为 true 时生效） |
| `block_images` | bool | `false` | 是否拦截图片资源加载，可显著提升速度 |
| `block_media` | bool | `false` | 是否拦截视频、音频、字体、CSS 等媒体和资源 |
| `user_agent` | string | `null` | 自定义浏览器 User-Agent |
| `stealth` | bool | `true` | 是否启用反检测插件，模拟真实人类行为 |
| `intercept_apis` | list | `[]` | 要拦截并提取数据的接口 URL 模式列表（支持正则） |
| `intercept_continue` | bool | `false` | 拦截接口后是否继续请求（默认 False 为中止请求） |
| `viewport` | object | `{"width": 1920, "height": 1080}` | 模拟的浏览器视口大小 |
| `storage_type` | string | `mongo` | 存储位置：`mongo` (默认) 或 `oss` (需配置凭据) |
| `save_html` | bool | `true` | 是否保存 HTML 源码 |
| `engine` | string | `playwright` | 浏览器引擎：`playwright` 或 `drissionpage` |
| `proxy` | object | `null` | 代理服务器配置，格式：`{"server": "...", "username": "...", "password": "..."}` |
| `proxy_pool_group` | string | `null` | 代理池分组名称，设置后将自动从中选择可用代理 |
| `cookies` | string/object/list | `null` | 注入 Cookie。支持字符串 (`name=val;`), JSON 对象 (`{name: val}`) 或 JSON 数组 (`[{name, value, ...}]`)。自动适配主域名。 |
| `cookie_group` | string | `null` | Cookie 池分组名称，设置后将自动从池中分配账号并注入 Cookie |
| `parser` | string | `null` | 解析服务类型：`gne` (通用新闻解析), `xpath` (自定义规则), `llm` (大模型解析) |
| `parser_config` | object | `null` | 解析配置。<br>• **gne**: 可选 `{"mode": "detail"}` (详情模式，默认) 或 `{"mode": "list"}` (列表模式)。<br>• **llm**: 必选 `{"fields": ["title", "price"]}` 指定提取字段。 |

#### **请求示例**

```json
{
  "url": "https://example.com",
  "params": {
    "wait_for": "networkidle",
    "screenshot": true,
    "block_images": true,
    "stealth": true,
    "cookies": "name=value; session=123",
    "intercept_apis": ["/api/v1/data/.*"],
    "proxy": {
      "server": "http://proxy.example.com:8080"
    }
  },
  "cache": {
    "enabled": true,
    "ttl": 3600
  }
}
```

### 2. 异步抓取 (POST /api/v1/scrape/async)

异步提交抓取任务，不等待执行结果，立即返回任务 ID。适用于耗时较长的任务或不需要即时响应的场景。

#### **请求体**
与同步抓取接口 (`/api/v1/scrape/`) 完全一致。

#### **响应示例**
```json
{
  "task_id": "65b2...",
  "url": "https://example.com",
  "status": "pending",
  "created_at": "2024-01-25T10:00:00"
}
```

### 3. 批量抓取 (POST /api/v1/scrape/batch)

支持一次性提交多个抓取任务。批量接口目前仅支持异步模式，不直接返回抓取结果。

#### **请求体**
```json
{
  "tasks": [
    {
      "url": "https://example.com/1",
      "params": { ... }
    },
    {
      "url": "https://example.com/2",
      "priority": 2
    }
  ]
}
```

### 4. 任务管理接口

用于查询异步/批量任务的执行状态和结果。

#### 4.1 获取任务详情

`GET /api/v1/tasks/{task_id}`

**查询参数 (Query Parameters):**

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `include_html` | `boolean` | `true` | 是否在结果中包含完整的 HTML 源码。数据量大时建议设置为 `false`。 |
| `include_screenshot` | `boolean` | `true` | 是否在结果中包含截图 Base64 数据。数据量大时建议设置为 `false`。 |

#### 4.2 接口列表

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/v1/tasks/{task_id}` | GET | 获取单个任务详情（包含抓取结果） |
| `/api/v1/tasks` | GET | 分页获取任务列表，支持状态/URL搜索 |
| `/api/v1/tasks/{task_id}/retry` | POST | 重试失败的任务 |
| `/api/v1/tasks/{task_id}` | DELETE | 删除指定任务 |
| `/api/v1/tasks/batch` | DELETE | 批量删除任务 |

### 5. 定时任务接口

用于管理自动化调度的抓取任务。

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/v1/schedules` | GET | 分页获取定时任务列表 |
| `/api/v1/schedules` | POST | 创建新的定时任务 |
| `/api/v1/schedules/{id}` | GET | 获取定时任务详情 |
| `/api/v1/schedules/{id}` | PUT | 更新定时任务配置 |
| `/api/v1/schedules/{id}` | DELETE | 删除定时任务 |
| `/api/v1/schedules/{id}/toggle` | POST | 切换任务状态（激活/暂停） |
| `/api/v1/schedules/{id}/run` | POST | 立即手动触发执行一次 |

### 6. 解析规则接口

用于维护结构化提取规则。

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/v1/rules` | GET | 获取解析规则列表 |
| `/api/v1/rules` | POST | 创建新解析规则 |
| `/api/v1/rules/{rule_id}` | PUT | 更新指定规则 |
| `/api/v1/rules/{rule_id}` | DELETE | 删除指定规则 |

## 📄 License

MIT
