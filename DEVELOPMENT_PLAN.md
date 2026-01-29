# Playwright 浏览器集群系统开发文档

## 项目概述

基于 Playwright 的分布式浏览器集群系统，提供网页渲染、数据抓取、缓存管理等功能，支持通过 API 接口调用浏览器进行页面抓取，返回渲染后的 HTML 内容。

### 核心功能
- 🔍 网页渲染抓取：通过 Playwright 自动化浏览器加载和渲染网页
- 📄 返回完整 HTML：返回 JavaScript 渲染后的完整页面 HTML
- 📊 任务队列管理：使用消息队列管理抓取任务
- 💾 结果缓存：缓存抓取结果，提升响应速度
- 🗄️ 数据持久化：MongoDB 存储任务历史和配置信息
- 🖥️ 后台管理界面：可视化管理和监控系统

---

## 技术选型

### 1. 后端框架
**选项 A：FastAPI（推荐）**
- 优点：高性能、异步支持好、自动生成 API 文档、类型安全
- 缺点：生态系统相对较新
- 适合：API 服务，需要高性能和异步处理

**选项 B：Flask**
- 优点：轻量级、成熟稳定、插件丰富
- 缺点：同步模型，需要额外配置实现异步
- 适合：简单应用，快速原型开发

**选项 C：Tornado**
- 优点：异步原生、高并发处理能力强
- 缺点：学习曲线陡峭，API 设计相对老旧
- 适合：高并发长连接场景

---

### 2. 任务队列系统
**选项 A：Redis + RQ（推荐）**
- 优点：轻量级、易于部署、支持任务优先级、失败重试
- 缺点：分布式支持相对较弱
- 适合：中小规模任务队列

**选项 B：RabbitMQ**
- 优点：成熟稳定、强大的路由功能、支持复杂的消息模式
- 缺点：部署复杂、资源占用较多
- 适合：企业级、复杂的消息路由场景

**选项 C：Celery + Redis/RabbitMQ**
- 优点：功能强大、支持定时任务、任务链、工作流
- 缺点：配置复杂、学习成本高
- 适合：复杂的异步任务处理场景

---

### 3. 缓存系统
**选项 A：Redis（推荐）**
- 优点：高性能、支持多种数据结构、持久化选项丰富
- 缺点：内存占用较大
- 适合：通用缓存场景

**选项 B：Memcached**
- 优点：简单高效、内存占用少
- 缺点：功能相对简单，不支持持久化
- 适合：简单的键值缓存

**选项 C：内存缓存（Python functools.lru_cache）**
- 优点：零配置、无需额外服务
- 缺点：仅限单进程、重启丢失、无过期策略
- 适合：开发环境、临时缓存

---

### 4. 浏览器管理方式
**选项 A：单进程动态启动（推荐）**
- 优点：实现简单、资源占用低、易于管理
- 缺点：并发能力有限、每次启动有开销
- 适合：中小并发、轻量级应用

**选项 B：浏览器池（Browser Pool）**
- 优点：复用浏览器实例、减少启动开销、提高并发能力
- 缺点：实现复杂、需要管理生命周期
- 适合：高并发场景

**选项 C：分布式浏览器节点**
- 优点：可水平扩展、高可用性
- 缺点：架构复杂、部署成本高
- 适合：大规模分布式系统

---

### 5. 后台管理界面
**选项 A：Vue 3 + Element Plus（推荐）**
- 优点：现代化框架、组件丰富、开发效率高
- 缺点：需要前端构建工具
- 适合：需要良好用户体验的现代 Web 应用

**选项 B：React + Ant Design**
- 优点：生态成熟、社区活跃
- 缺点：学习曲线较陡峭
- 适合：大型企业应用

**选项 C：FastAPI Admin**
- 优点：与 FastAPI 集成好、快速开发
- 缺点：定制能力有限
- 适合：快速原型、简单管理后台

**选项 D：Streamlit**
- 优点：纯 Python、开发极快
- 缺点：定制能力弱、不适合复杂交互
- 适合：数据监控面板、快速原型

---

### 6. 数据库
**选项 A：MongoDB（已确定）**
- 优点：灵活的文档模型、易于扩展
- 缺点：事务支持相对弱
- 适合：存储任务历史、配置信息等非结构化数据

---

## 系统架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端应用                              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI 服务层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ API 接口      │  │ 任务调度     │  │ 缓存管理     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          │ 检查缓存         │                  │
          ▼                  │                  │
    ┌─────────┐              │                  │
    │ Redis   │◄─────────────┤                  │
    └─────────┘              │                  │
                             │                  │
                             │ 添加任务          │
                             ▼                  │
                      ┌────────────┐           │
                      │ 任务队列    │           │
                      └─────┬──────┘           │
                            │                  │
                            │ Worker 消费      │
                            ▼                  │
┌──────────────────────────────────────────────────────────────┐
│                    Playwright Worker                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 浏览器管理    │  │ 页面抓取     │  │ 结果处理     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          │                  │                  │
          ▼                  ▼                  ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │Browser  │        │HTML 渲染│        │存储结果 │
    │  Pool   │        │         │        │         │
    └─────────┘        └─────────┘        └─────────┘
                                                  │
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │    MongoDB      │
                                         │ ┌─────────────┐ │
                                         │ │ 任务历史     │ │
                                         │ │ 配置信息     │ │
                                         │ │ 错误日志     │ │
                                         │ └─────────────┘ │
                                         └─────────────────┘
                                                  │
                                                  │
                                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                   后台管理界面                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 任务监控     │  │ 任务历史     │  │ 配置管理     │       │
│  │              │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

---

## 数据库设计

### MongoDB 集合设计

#### 1. tasks（任务表）
```javascript
{
  _id: ObjectId,
  url: String,              // 目标 URL
  status: String,          // pending, processing, success, failed
  priority: Number,        // 优先级
  params: Object,          // 抓取参数（等待时间、选择器等）
  result: {
    html: String,          // 渲染后的 HTML
    screenshot: String,    // 截图（可选，base64）
    metadata: Object       // 元数据（标题、加载时间等）
  },
  error: {
    message: String,       // 错误信息
    stack: String          // 错误堆栈
  },
  cache_key: String,       // 缓存键
  created_at: DateTime,
  updated_at: DateTime,
  completed_at: DateTime
}
```

#### 2. task_stats（任务统计）
```javascript
{
  _id: ObjectId,
  date: Date,              // 统计日期
  total: Number,           // 总任务数
  success: Number,         // 成功数
  failed: Number,          // 失败数
  avg_duration: Number     // 平均耗时（秒）
}
```

#### 3. configs（配置表）
```javascript
{
  _id: ObjectId,
  key: String,             // 配置键
  value: Object,           // 配置值
  description: String,     // 配置描述
  updated_at: DateTime
}
```

---

## API 接口设计

### 1. 抓取网页
```
POST /api/v1/scrape
```

**请求参数：**
```json
{
  "url": "https://example.com",
  "params": {
    "wait_for": "networkidle",  // 等待策略：networkidle, load, domcontentloaded
    "wait_time": 3000,          // 额外等待时间（毫秒）
    "timeout": 30000,           // 超时时间（毫秒）
    "selector": null,           // 等待特定选择器（可选）
    "screenshot": false,        // 是否截图
    "block_images": false,      // 是否阻塞图片
    "block_media": false,       // 是否阻塞媒体
    "user_agent": null,         // 自定义 User-Agent
    "viewport": {               // 视口大小
      "width": 1920,
      "height": 1080
    },
    "proxy": {
        "server": "http://proxy.example.com:8080",
        "username": "your_username",  // 可选
        "password": "your_password"   // 可选
    },
  },
  "cache": {
    "enabled": true,            // 是否启用缓存
    "ttl": 3600                 // 缓存过期时间（秒）
  },
  "priority": 1                 // 任务优先级（数字越大优先级越高）
}
```

**响应：**
```json
{
  "task_id": "507f1f77bcf86cd799439011",
  "status": "success",
  "result": {
    "html": "<!DOCTYPE html>...",
    "metadata": {
      "title": "页面标题",
      "url": "https://example.com",
      "load_time": 2.34,
      "timestamp": "2024-01-01T00:00:00Z"
    }
  },
  "cached": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 2. 异步抓取网页
```
POST /api/v1/scrape/async
```

**请求参数：**同上

**响应：**
```json
{
  "task_id": "507f1f77bcf86cd799439011",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 3. 查询任务状态
```
GET /api/v1/tasks/{task_id}
```

**响应：**
```json
{
  "task_id": "507f1f77bcf86cd799439011",
  "url": "https://example.com",
  "status": "completed",
  "result": {
    "html": "<!DOCTYPE html>...",
    "metadata": {
      "title": "页面标题",
      "load_time": 2.34
    }
  },
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:03Z"
}
```

---

### 4. 批量抓取
```
POST /api/v1/scrape/batch
```

**请求参数：**
```json
{
  "tasks": [
    { "url": "https://example1.com", "params": {...} },
    { "url": "https://example2.com", "params": {...} }
  ]
}
```

**响应：**
```json
{
  "task_ids": [
    "507f1f77bcf86cd799439011",
    "507f1f77bcf86cd799439012"
  ]
}
```

---

### 5. 获取统计数据
```
GET /api/v1/stats
```

**响应：**
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
  }
}
```

---

### 6. 清除缓存
```
DELETE /api/v1/cache/{cache_key}
```

---

### 7. 配置管理
```
GET    /api/v1/configs
POST   /api/v1/configs
PUT    /api/v1/configs/{key}
DELETE /api/v1/configs/{key}
```

---

## 项目目录结构

```
browser_cluster/
├── app/
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── scrape.py          # 抓取接口
│   │   ├── tasks.py           # 任务管理接口
│   │   └── admin.py           # 管理接口
│   ├── core/                   # 核心功能
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── browser.py         # 浏览器管理
│   │   └── scraper.py         # 抓取逻辑
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── task.py
│   │   └── config.py
│   ├── services/               # 业务逻辑
│   │   ├── __init__.py
│   │   ├── queue_service.py   # 队列服务
│   │   ├── cache_service.py   # 缓存服务
│   │   └── worker.py          # Worker
│   ├── db/                     # 数据库
│   │   ├── __init__.py
│   │   ├── mongo.py           # MongoDB 连接
│   │   └── redis.py           # Redis 连接
│   └── main.py                 # FastAPI 应用入口
├── admin/                      # 后台管理界面
│   ├── src/
│   │   ├── components/        # Vue 组件
│   │   ├── views/             # 页面
│   │   ├── api/               # API 调用
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
├── tests/                      # 测试
│   ├── __init__.py
│   ├── test_api.py
│   └── test_scraper.py
├── scripts/                    # 脚本
│   ├── start_worker.py        # 启动 Worker
│   └── init_db.py             # 初始化数据库
├── .env                        # 环境变量
├── .env.example
├── requirements.txt            # Python 依赖
├── pyproject.toml             # 项目配置
├── docker-compose.yml         # Docker 编排
├── Dockerfile
└── README.md
```

---

## 开发流程

### 第一阶段：项目初始化
1. 创建项目目录结构
2. 配置 Python 虚拟环境
3. 安装依赖（FastAPI, Playwright, MongoDB, Redis 等）
4. 配置环境变量
5. 初始化数据库连接

### 第二阶段：核心功能开发
1. 实现 MongoDB 和 Redis 连接管理
2. 实现浏览器管理模块
3. 实现抓取逻辑（Playwright）
4. 实现任务队列服务
5. 实现 Worker 进程
6. 实现 API 接口

### 第三阶段：缓存和持久化
1. 实现缓存服务
2. 实现任务状态更新
3. 实现统计数据收集
4. 实现错误处理和日志记录

### 第四阶段：后台管理界面
1. 初始化前端项目
2. 实现任务监控页面
3. 实现任务历史页面
4. 实现配置管理页面
5. 实现统计图表展示

### 第五阶段：测试和优化
1. 编写单元测试
2. 编写集成测试
3. 性能测试和优化
4. 错误处理完善
5. 日志系统完善

### 第六阶段：部署和文档
1. 编写 Docker 配置
2. 编写部署文档
3. 编写 API 文档
4. 编写用户手册

---

## 环境变量配置

```bash
# FastAPI 配置
APP_NAME=BrowserCluster
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# MongoDB 配置
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=browser_cluster

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_URL=redis://localhost:6379/1

# Playwright 配置
BROWSER_TYPE=chromium          # chromium, firefox, webkit
HEADLESS=True
BLOCK_IMAGES=False
BLOCK_MEDIA=False
DEFAULT_TIMEOUT=30000
DEFAULT_WAIT_FOR=networkidle

# Worker 配置
WORKER_CONCURRENCY=3           # 并发 Worker 数量
MAX_RETRIES=3                  # 最大重试次数
RETRY_DELAY=5                  # 重试延迟（秒）

# 缓存配置
CACHE_ENABLED=True
DEFAULT_CACHE_TTL=3600         # 默认缓存过期时间（秒）

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

## 依赖清单

### Python 依赖
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
playwright==1.40.0
pymongo==4.6.0
redis==5.0.1
rq==1.15.1
httpx==0.25.2
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Node.js 依赖（前端）
```json
{
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "element-plus": "^2.4.0",
    "echarts": "^5.4.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0"
  }
}
```

---

## Docker 部署方案

```yaml
# docker-compose.yml
version: '3.8'

services:
  fastapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongo:27017/
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongo
      - redis
    volumes:
      - ./logs:/app/logs

  worker:
    build: .
    command: python scripts/start_worker.py
    environment:
      - MONGO_URI=mongodb://mongo:27017/
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongo
      - redis
    volumes:
      - ./logs:/app/logs

  mongo:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  admin:
    build: ./admin
    ports:
      - "5173:5173"

volumes:
  mongo_data:
  redis_data:
```

---

## 功能优先级

### P0（核心功能）
1. ✅ 基础网页抓取（Playwright）
2. ✅ 任务队列管理
3. ✅ 结果缓存
4. ✅ MongoDB 持久化
5. ✅ API 接口（抓取、查询状态）

### P1（重要功能）
1. ⏳ 异步抓取支持
2. ⏳ 批量抓取
3. ⏳ 错误重试机制
4. ⏳ 统计数据收集

### P2（增强功能）
1. ⏳ 后台管理界面
2. ⏳ 截图功能
3. ⏳ 自定义 User-Agent
4. ⏳ 资源阻塞配置

### P3（可选功能）
1. ⏳ 代理支持
2. ⏳ Cookie 管理
3. ⏳ 验证码处理
4. ⏳ 任务调度（定时任务）

---

## 技术难点和解决方案

### 1. 浏览器实例管理
**问题：**频繁启动和关闭浏览器会导致性能问题和资源泄漏
**解决方案：**
- 实现浏览器池，复用浏览器实例
- 定期清理长时间运行的浏览器
- 监控内存使用情况，超限自动重启

### 2. 并发控制
**问题：**过多的并发任务可能导致系统资源耗尽
**解决方案：**
- 使用信号量控制并发数
- 限制每个 Worker 的浏览器实例数量
- 实现任务优先级队列

### 3. 缓存一致性
**问题：**如何保证缓存和数据库的一致性
**解决方案：**
- 使用 Redis 作为缓存层
- 设置合理的 TTL
- 实现缓存失效策略

### 4. 错误处理
**问题：**网络超时、页面加载失败等异常情况处理
**解决方案：**
- 实现自动重试机制
- 记录详细错误日志
- 提供错误回调通知

---

## 性能优化建议

1. **浏览器复用**：使用浏览器池，减少启动开销
2. **资源阻塞**：根据需要阻塞图片、媒体等资源，加快加载速度
3. **并发控制**：根据服务器配置调整并发数
4. **缓存策略**：合理设置缓存过期时间，平衡实时性和性能
5. **异步处理**：使用异步 I/O 提高吞吐量
6. **CDN 加速**：前端资源使用 CDN
7. **数据库索引**：为常用查询字段添加索引

---

## 安全建议

1. **输入验证**：严格验证 URL 格式和参数
2. **速率限制**：实现 API 速率限制，防止滥用
3. **认证授权**：管理接口需要身份认证
4. **HTTPS**：生产环境使用 HTTPS
5. **CORS 配置**：合理配置 CORS 策略
6. **敏感信息**：不在日志中记录敏感信息
7. **依赖更新**：定期更新依赖，修复安全漏洞

---

## 下一步行动

请从以下技术选型中进行选择（可回复序号或组合）：

1. **后端框架**：A (FastAPI) / B (Flask) / C (Tornado)
2. **任务队列**：A (Redis + RQ) / B (RabbitMQ) / C (Celery)
3. **缓存系统**：A (Redis) / B (Memcached) / C (内存缓存)
4. **浏览器管理**：A (单进程动态) / B (浏览器池) / C (分布式节点)
5. **后台界面**：A (Vue3 + Element Plus) / B (React + AntD) / C (FastAPI Admin) / D (Streamlit)

确认选型后，我将开始项目开发。
