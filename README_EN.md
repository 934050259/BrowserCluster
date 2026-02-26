# Browser Cluster

<p align="center">
  <a href="README.md">中文</a> | <strong>English</strong>
</p>

> [!IMPORTANT]
> **The project is in its early stages and may have bugs. Please submit issues actively, and the author will update as soon as possible!**

<p align="center">
  <img src="admin/public/chat.png" width="200" alt="Author Image">
</p>

<p align="center">
  <strong>Contact the author, welcome to join the project exchange group~</strong><br>
</p>

**Browser Cluster** is a high-performance, distributed browser automation cluster system built on **Playwright**, **DrissionPage**, and FastAPI. It supports large-scale concurrent web scraping, screenshots, parsing, and automation. It features a **built-in intelligent proxy pool and automatic detection mechanism**, specifically optimized for difficult anti-scraping websites like Cloudflare. It provides comprehensive task scheduling, result caching, node monitoring, and proxy status maintenance.

![UI Preview](admin/public/image.png)

## 🚀 Core Features

- **Dual Browser Engine Support**: Support switching between Playwright and DrissionPage engines.
    - **Playwright**: Ideal for complex automation interactions and API interception.
    - **DrissionPage**: Strong native anti-detection, easily bypasses Cloudflare 5-second shield and various CAPTCHAs.
- **Distributed Architecture**: Supports horizontal scaling of multiple Worker nodes to handle high-concurrency scenarios easily.
- **Stealth and Anti-Detection**:
    - Playwright has a built-in Stealth plugin.
    - DrissionPage uses browser fingerprint erasing technology and supports deep hiding in Linux environments.
- **Efficient Caching**: Redis-based result caching mechanism with customizable TTL.
- **Resource Optimization**: Intelligent interception of images and media resources to significantly speed up rendering.
- **API Interception**: Supports extracting specific XHR/Fetch interface data during the rendering process.
- **OSS Cloud Storage Support**:
    - Automatically upload scraped HTML source code and page screenshots to Alibaba Cloud OSS.
    - Resolves large-scale data storage pressure and supports secure access to private buckets.
    - The backend automatically proxies OSS content to resolve cross-origin and permission issues for direct frontend access.
- **Intelligent Proxy Pool Management**:
    - Supports proxy access for various protocols including HTTP/HTTPS/SOCKS5.
    - Supports tunnel proxies and static proxies with built-in automatic authentication logic.
    - **Multi-level Proxy Inheritance**: Scraping tasks can automatically inherit proxy pools configured in parsing rules, simplifying the configuration process.
    - **One-click Full Detection**: Supports manual triggering or scheduled automatic detection of proxy availability.
    - **Automatic Status Maintenance**: Automatically circuit-breaks unavailable proxies based on detection results to ensure a high success rate for scraping tasks.
- **High-Availability Distributed Worker**:
    - **Auto-reconnection Mechanism**: Workers can automatically reconnect to RabbitMQ upon disconnection, effectively handling network fluctuations.
    - **Multi-instance Load Balancing**: Supports multiple Worker instances running simultaneously, automatically competing for task queue processing.
- **Automated Scheduling**: Built-in task scheduling engine supporting Interval and Cron expressions for periodic data collection.
- **Multi-mode Parsing and Extraction**: Integrates various structured data extraction technologies to adapt to web pages of different complexities:
    - **Intelligent General Extraction (GNE)**: Based on content extraction algorithms, supports two modes:
        - **Detail Mode**: Automatically extracts title, content, publish time, and author from news-like websites.
        - **List Mode**: Automatically identifies and extracts titles, links, and dates from news list pages.
    - **Precise Rule Parsing (XPath/CSS)**: Supports visual configuration of XPath and CSS selectors for pixel-perfect extraction from structured pages like e-commerce or list pages.
    - **Advantages of AI Intelligent Extraction**:
        - ✅ **Zero-code Configuration**: Just enter the URL, and AI automatically analyzes the page structure and generates XPath rules.
        - ✅ **Intelligent Recognition**: Automatically identifies list containers, titles, links, times, and other key fields.
        - ✅ **Full Load Guarantee**: Automatically waits for the page to fully load (supports custom wait time) when fetching HTML to ensure complete analysis.
        - ✅ **Visual Verification**: Generated rules can be verified and fine-tuned in real-time on the interface.
    - **Large Language Model Parsing (LLM)**: Combines LLMs like OpenAI/DeepSeek to achieve semantic extraction of complex web pages through natural language descriptions of required fields, with zero code.
- **Visual Management**: Provides a modern management dashboard based on Vue 3 + Element Plus.
    - **Seamless Refresh Experience**: Deep cache optimization for task management and scraping record pages, supporting automatic data refresh and synchronization in `keep-alive` mode.
    - **Parsing Transparency**: Scraping record details show the matched parsing rule domain in real-time, providing a clear understanding of the source logic for each piece of data.

## 🛠️ Technology Stack

- **Backend**: Python 3.10, FastAPI, Playwright, RabbitMQ, MongoDB, Redis
- **Frontend**: Vue 3, Element Plus, Pinia, Vite
- **Deployment**: Docker (Multi-stage build)

## 🏗️ System Architecture

![Architecture](admin/public/app.jpeg)

### 🔄 Task Processing Flow

![Architecture](admin/public/architecture.png)

1. **Request Access and Validation (Entry)**
   - `API Gateway` receives HTTP requests, performs **JWT authentication**, and validates parameter legality.
   - `Task Scheduler` periodically triggers preset tasks, bypassing gateway authentication and entering the distribution flow directly.
   - Check **Redis Cache**: If it hits the cache and hasn't expired, return the result directly, skipping subsequent steps.

2. **Task Persistence and Distribution (Dispatch)**
   - API generates a globally unique `task_id` and initializes the task status (pending) in **MongoDB**.
   - **Intelligent Routing and Proxy Preselection**: Preselects available proxies from **proxy configurations** based on task targets and settings.
   - Publishes the task payload to the **RabbitMQ** priority queue to achieve traffic shaving.
   - Synchronous interfaces enter a waiting state, while asynchronous interfaces return the `task_id` immediately.

3. **Intelligent Scheduling and Execution (Execution)**
   - Idle `Worker` nodes listen to the queue and compete for tasks based on **task priority**.
   - Worker calls **Browser Manager** to allocate an independent browser context:
     - **Proxy Injection and Health Check**: Dynamically injects encrypted proxies and verifies connectivity; triggers **automatic retry/replacement** if the proxy fails.
     - **Environment Simulation**: Injects Stealth scripts, configures simulated fingerprints and viewports.
     - **Resource Interception**: Intercepts images/media according to configuration to speed up rendering.
     - **Real-time Interception**: Registers API interception listeners to capture XHR/Fetch data.

4. **Multi-mode Parsing (Parsing)**
   - After the page loads (according to the `wait_for` strategy), the Worker retrieves the rendered DOM.
   - Executes the parsing engine based on the `parser` configuration:
     - **GNE**: Automatically extracts content and metadata.
     - **XPath/CSS**: Performs precise extraction according to rules.
     - **LLM**: Calls large models for semantic field mapping.

5. **Result Archiving and Feedback (Feedback)**
   - **Success Handling**: Writes HTML, structured data, screenshots, and performance metrics to MongoDB.
   - **Proxy Status Feedback**: Real-time feedback to the proxy pool based on execution results, triggering proxy **circuit-breaking or weight adjustment**.
   - **Result Archiving**: Synchronizes results to Redis (with TTL) to speed up subsequent identical requests.
   - **Exception Handling**: If execution fails, records the error stack and triggers a **retry mechanism** (optional).
   - **Statistics Update**: Reports task status in real-time and updates **Prometheus/Stats** monitoring data.

### Core Components

- **🌐 API Gateway (FastAPI)**
  - Unified entry point for the system, responsible for receiving HTTP requests, parameter validation, and task scheduling.
  - Integrates a Redis caching layer to return cached results for duplicate requests, significantly reducing system load.
  - Provides comprehensive APIs for task management, node monitoring, and system configuration.

- **⏰ Task Scheduler (APScheduler)**
  - Built-in high-performance task scheduling engine supporting large-scale concurrent scheduled tasks.
  - Supports real-time task status control (enable/disable), manual immediate triggering, and execution history tracking.
  - Provides two flexible scheduling strategies: Interval and Cron.

- **📨 Message Queue (RabbitMQ)**
  - Asynchronous task bus, achieving complete decoupling between producers (API) and consumers (Worker).
  - Supports task persistence, priority queues, and ACK mechanisms to ensure task reliability under high concurrency.

- **🤖 Worker Nodes (Playwright & DrissionPage)**
  - Distributed execution units supporting containerized deployment and horizontal scaling.
  - Responsible for launching browser contexts, performing page rendering, interaction, screenshots, and data extraction.
  - **Dual Engine Driven**: Dynamically chooses Playwright or DrissionPage based on task parameters.
  - **Singleton Mode Optimization**: Browser instances are resident and reused, managing tasks through tabs, greatly reducing resource overhead and startup latency.
  - Built-in **Stealth Mode** and resource interception strategies to optimize scraping success rate and speed.

- **💾 Data Storage**
  - **MongoDB**: Stores full task records, scraping results, node statuses, and system configurations.
  - **Redis**: Used for hot data caching and distributed locking to improve system response speed.

- **🖥️ Admin Dashboard (Vue 3)**
  - **Statistics Monitoring**: Real-time display of task success rates, processing durations, and queue backlog.
  - **Proxy Management**: Visual maintenance of the proxy pool, supporting immediate detection and batch import.
  - **Task Management**: Full task history traceability, supporting result preview and error log viewing.
  - **Node Management**: Monitors cluster Worker status, load conditions, and resource usage, supporting node online/offline management.
  - **Parsing Rules**: Visual maintenance of parsing templates for each website, supporting online testing of rule validity.
  - **Configuration Management**: Dynamically adjust browser concurrency, timeouts, and global proxy settings, supporting one-click initialization of system configurations to the database.
- **User Management**: Role-Based Access Control (RBAC) to ensure system security.

## 📦 Quick Start

### Prerequisites

- Python 3.10
- Node.js 22 
- RabbitMQ, MongoDB, Redis

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/934050259/BrowserCluster.git
   cd browser-cluster
   ```

2. **Environment Configuration**
   Copy the example configuration file and modify it according to your actual environment:
   ```bash
   cp .env.example .env
   # Windows (PowerShell)
   # copy .env.example .env
   ```
   
   Modify the database and message queue connection information in the `.env` file:
   ```ini
   MONGO_URI=mongodb://localhost:27017/
   REDIS_URL=redis://localhost:6379/0
   REDIS_CACHE_URL=redis://localhost:6379/1
   RABBITMQ_URL=amqp://guest:guest@localhost:5672/
   ```

3. **Initialize Configuration and Account**
   Run the initialization scripts to import default configurations and create the initial administrator account:
   ```bash
   # Initialize system configuration
   python scripts/init_configs_db.py

   # Initialize default administrator account (User: admin, Password: admin)
   python scripts/init_admin.py
   ```

4. **Backend Setup**
   ```bash
   # Install dependencies
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   playwright install chromium

   # Start API service
   uvicorn app.main:app --reload
   ```

5. **Worker Startup**
   Workers are responsible for receiving and executing actual web scraping tasks from the message queue:
   ```bash
   # Start Worker process
   python scripts/start_worker.py
   ```
   Alternatively, add and start workers within the admin dashboard's Node Management section.

6. **Frontend Setup**
   ```bash
   cd admin
   npm install
   npm run build  # After building, it's hosted by the backend, or run npm run dev for development
   ```

7. **Access the System**
   - Admin Dashboard: `http://localhost:8000` (hosted by backend) or `http://localhost:5173` (Vite dev mode)
   - API Docs: `http://localhost:8000/docs`

## 🐳 Docker Deployment

This project supports multi-stage builds, with frontend static resources and backend services integrated into the image.

### 1. Build the Image

Run the following command in the project root directory to build, without needing to configure `.env` beforehand:

```powershell
docker build -t browser-cluster:latest .
```

### 2. Run the Container

Pass configuration parameters through environment variables when starting the container. Database and system configuration initialization will execute automatically upon startup.

#### Start API Service (including Admin Dashboard)

If you want the fastest startup, you can run the following command directly (without mounting volumes):

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

> **💡 Regarding data and logs directories:**
> - **Without mounting**: The system will still run normally. The program will automatically create `data` (storing configurations and accounts) and `logs` (storing logs) folders inside the container.
> - **Disadvantage**: When you delete and recreate the container, configurations modified in the Web interface and newly created users will be **lost** (restored to default state).
> - **Recommendation**: If running in a production environment or wanting to persist configurations, it's recommended to add directory mounting: `-v ${PWD}/data:/app/data -v ${PWD}/logs:/app/logs`.

## ⚙️ Configuration Description

Main configuration items (can be set via `.env` or environment variables):

### 1. Basic Environment Configuration

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEBUG` | `true` | Whether to enable debug mode (output detailed logs) |
| `HOST` | `0.0.0.0` | Service listening address |
| `PORT` | `8000` | Service listening port |
| `SECRET_KEY` | `your-secret-key` | System security key (strongly recommended to change in production) |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection address |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis task queue/status connection address |
| `REDIS_CACHE_URL` | `redis://localhost:6379/1` | Redis result cache connection address |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection address |

### 2. Browser and Execution Configuration

| Variable | Default | Description |
| :--- | :--- | :--- |
| `BROWSER_TYPE` | `chromium` | Default browser type (currently only `chromium` is supported) |
| `HEADLESS` | `true` | Whether to enable headless mode |
| `STEALTH_MODE` | `true` | Whether to enable anti-crawler stealth mode |
| `DEFAULT_TIMEOUT` | `30000` | Default task timeout (milliseconds) |
| `WORKER_CONCURRENCY` | `3` | Concurrent tasks per Worker node |
| `NODE_ID` | `node-1` | Unique node identifier |

### 3. OSS Storage Configuration (Optional)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OSS_ENABLED` | `false` | Whether to enable OSS storage (stores results in the cloud) |
| `OSS_ENDPOINT` | - | OSS access domain (e.g., `oss-cn-hangzhou.aliyuncs.com`) |
| `OSS_ACCESS_KEY_ID` | - | OSS AccessKey ID |
| `OSS_ACCESS_KEY_SECRET` | - | OSS AccessKey Secret |
| `OSS_BUCKET_NAME` | - | OSS Bucket name |

### 4. LLM Model Configuration (Optional)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LLM_API_BASE` | `https://api.openai.com/v1` | LLM API base address |
| `LLM_API_KEY` | - | LLM API key |
| `LLM_MODEL` | `gpt-3.5-turbo` | Model name used |

## 📝 Task Parameter Description

> **Submission Format Note**: All scraping interfaces (synchronous, asynchronous, batch) in this system use **JSON** format. Request headers must include `Content-Type: application/json`, and parameters must be placed in the HTTP request body.
> 
> - **Python (requests)**: Use `json={...}` to pass parameters.
> - **JavaScript (Axios)**: Pass the object directly `axios.post(url, {...})`.

### 1. Scraping Interface (POST /api/v1/scrape/)

This is the core interface, supporting synchronous scraping and returning rendered results.

#### **Request Body (JSON)**

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `url` | string | Yes | - | Full target webpage URL |
| `params` | object | No | `{}` | Detailed scraping configuration (see table below) |
| `cache` | object | No | `{"enabled": true, "ttl": 3600}` | Cache configuration (see table below) |
| `priority` | int | No | `1` | Task priority, higher numbers processed first |

#### **cache Configuration Details**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled` | bool | `true` | Whether to enable cache |
| `ttl` | int | `3600` | Cache expiration time (seconds), default 1 hour |

#### **params Configuration Details**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `wait_for` | string | `networkidle` | Wait strategy: `networkidle`, `load`, `domcontentloaded` |
| `wait_time` | int | `3000` | Extra wait time after page load (ms) for async rendering |
| `timeout` | int | `30000` | Total scraping timeout (ms) |
| `selector` | string | `null` | Wait for a specific CSS selector before returning |
| `screenshot` | bool | `false` | Whether to generate page screenshot |
| `is_fullscreen` | bool | `false` | Full-screen screenshot (only if `screenshot` is true) |
| `block_images` | bool | `false` | Whether to block image resources for speed |
| `block_media` | bool | `false` | Whether to block video, audio, fonts, CSS, etc. |
| `user_agent` | string | `null` | Custom browser User-Agent |
| `stealth` | bool | `true` | Enable anti-detection plugin to simulate humans |
| `intercept_apis` | list | `[]` | List of URL patterns to intercept and extract (regex supported) |
| `intercept_continue` | bool | `false` | Whether to continue request after interception (default False aborts) |
| `viewport` | object | `{"width": 1920, "height": 1080}` | Simulated browser viewport size |
| `storage_type` | string | `mongo` | Storage location: `mongo` (default) or `oss` |
| `save_html` | bool | `true` | Whether to save HTML source code |
| `engine` | string | `playwright` | Browser engine: `playwright` or `drissionpage` |
| `proxy` | object | `null` | Proxy server config: `{"server": "...", "username": "...", "password": "..."}` |
| `cookies` | string/obj/list | `null` | Inject Cookies. Supports string, JSON object, or JSON array. |
| `parser` | string | `null` | Parser type: `gne`, `xpath`, `llm` |
| `parser_config` | object | `null` | Parser config.<br>• **gne**: `{"mode": "detail"}` or `{"mode": "list"}`.<br>• **llm**: `{"fields": ["title", "price"]}` is required. |

#### **Request Example**

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

### 2. Asynchronous Scraping (POST /api/v1/scrape/async)

Asynchronously submit scraping tasks, returning a task ID immediately without waiting for results. Suitable for time-consuming tasks or scenarios not requiring immediate responses.

#### **Request Body**
Identical to the synchronous scraping interface (`/api/v1/scrape/`).

#### **Response Example**
```json
{
  "task_id": "65b2...",
  "url": "https://example.com",
  "status": "pending",
  "created_at": "2024-01-25T10:00:00"
}
```

### 3. Batch Scraping (POST /api/v1/scrape/batch)

Submit multiple scraping tasks at once. Currently only supports asynchronous mode.

#### **Request Body**
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

### 4. Task Management Interface

Used to query execution status and results of asynchronous/batch tasks.

#### 4.1 Get Task Details

`GET /api/v1/tasks/{task_id}`

**Query Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `include_html` | `boolean` | `true` | Include full HTML source in the result. |
| `include_screenshot` | `boolean` | `true` | Include screenshot Base64 data in the result. |

#### 4.2 Interface List

| Interface | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/tasks/{task_id}` | GET | Get single task details (including results) |
| `/api/v1/tasks` | GET | Paginated task list, supports status/URL search |
| `/api/v1/tasks/{task_id}/retry` | POST | Retry a failed task |
| `/api/v1/tasks/{task_id}` | DELETE | Delete specified task |
| `/api/v1/tasks/batch` | DELETE | Batch delete tasks |

### 5. Scheduled Task Interface

Used to manage automatically scheduled scraping tasks.

| Interface | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/schedules` | GET | Paginated list of scheduled tasks |
| `/api/v1/schedules` | POST | Create a new scheduled task |
| `/api/v1/schedules/{id}` | GET | Get scheduled task details |
| `/api/v1/schedules/{id}` | PUT | Update scheduled task configuration |
| `/api/v1/schedules/{id}` | DELETE | Delete scheduled task |
| `/api/v1/schedules/{id}/toggle` | POST | Toggle task status (Active/Paused) |
| `/api/v1/schedules/{id}/run` | POST | Manually trigger execution once immediately |

### 6. Parsing Rules Interface

Used to maintain structured extraction rules.

| Interface | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/rules` | GET | Get parsing rule list |
| `/api/v1/rules` | POST | Create new parsing rule |
| `/api/v1/rules/{rule_id}` | PUT | Update specified rule |
| `/api/v1/rules/{rule_id}` | DELETE | Delete specified rule |

## 📄 License

MIT
