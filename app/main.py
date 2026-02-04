"""
FastAPI 应用主模块

创建和配置 FastAPI 应用，注册路由、中间件等
"""
import os
import sys
import asyncio
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware



# Windows 平台下，Playwright 需要使用 ProactorEventLoopPolicy 才能正常启动子进程
if sys.platform == 'win32':
    # 尽可能早地设置策略
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.api import scrape, tasks, stats, admin, nodes, auth, users, rules, schedules
from app.db.mongo import mongo
from app.db.redis import redis_client
from app.core.config import settings
from app.core.logger import setup_logging
from app.services.node_manager import node_manager
from app.services.scheduler_service import scheduler_service

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Playwright-based distributed browser cluster"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应限制）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    import time
    from fastapi.responses import Response
    
    # 记录请求开始时间
    start_time = time.time()
    
    # 提取请求信息
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query_params = dict(request.query_params)
    
    # 调用下一个中间件或路由处理函数
    response = await call_next(request)
    
    # 记录响应信息
    status_code = response.status_code
    process_time = time.time() - start_time
    
    # 构建日志消息
    log_message = f"API访问日志 | {client_ip} | {method} {path} | {status_code} | {process_time:.3f}s"
    
    # 如果有查询参数，添加到日志中
    if query_params:
        log_message += f" | 查询参数: {query_params}"
    
    # 根据状态码选择日志级别
    if status_code >= 500:
        logger.error(log_message)
    elif status_code >= 400:
        logger.warning(log_message)
    else:
        logger.info(log_message)
    
    return response

# 注册 API 路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(scrape.router)
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(nodes.router)
app.include_router(rules.router)
app.include_router(schedules.router)


@app.on_event("startup")
async def startup_event():
    """应用启动事件：初始化数据库连接"""
    # 打印当前事件循环类型以便调试 Windows 兼容性问题
    loop = asyncio.get_running_loop()
    logger.info(f"Current event loop: {type(loop).__name__}")
    
    # 从数据库加载配置
    settings.load_from_db()
    
    mongo.connect()
    redis_client.connect_cache()
    
    # 自动启动离线但状态为 running 的节点
    await node_manager.auto_start_nodes()
    
    # 启动定时任务调度器
    scheduler_service.start()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件：清理数据库连接"""
    # 停止定时任务调度器
    scheduler_service.stop()
    
    mongo.close()
    redis_client.close_all()


@app.get("/api")
async def root():
    """
    根路径接口

    Returns:
        dict: 应用基本信息
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        dict: 健康状态
    """
    return {"status": "healthy"}


# 静态资源托管（用于 Docker 部署或本地 build 后访问）
# 优先检查 static 目录，再检查 admin/dist 目录
static_dir = "static"
if not os.path.exists(static_dir) and os.path.exists("admin/dist"):
    static_dir = "admin/dist"

if os.path.exists(static_dir):
    # 挂载 assets 目录
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # SPA 路由兜底处理
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除 API 请求
        if full_path.startswith("api/"):
            return {"error": "Not Found", "status": 404}
            
        # 尝试返回静态文件（如 favicon.ico）
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # 默认返回 index.html
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    # 在 Windows 上强制指定 loop="asyncio" 配合 Proactor 策略
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        loop="asyncio"
    )
