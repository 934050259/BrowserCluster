"""
FastAPI 应用主模块

创建和配置 FastAPI 应用，注册路由、中间件等
"""
import os
import sys
import asyncio

# Windows 平台下，Playwright 需要使用 ProactorEventLoopPolicy 才能正常启动子进程
# 必须在任何 asyncio 相关的库导入之前设置
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.api import scrape, tasks, stats, admin, nodes, auth, users, rules, schedules, proxy, scrapers
from app.db.mongo import mongo
from app.db.redis import redis_client
from app.core.config import settings
from app.core.logger import setup_logging
from app.services.node_manager import node_manager
from app.services.scheduler_service import scheduler_service
from app.services.proxy_service import proxy_service
from app.core.scheduler import scraper_scheduler
from app.core.drission_browser import drission_manager
from app.core.browser import browser_manager

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

# 请求日志中间件 (使用原生的 ASGI 中间件以避免 BaseHTTPMiddleware 与 StreamingResponse/FileResponse 的冲突)
class RequestLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()
        
        # 提取请求信息
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        method = scope.get("method")
        path = scope.get("path")
        query_string = scope.get("query_string", b"").decode()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.time() - start_time
                
                # 构建日志消息
                log_message = f"API访问日志 | {client_ip} | {method} {path} | {status_code} | {process_time:.3f}s"
                if query_string:
                    log_message += f" | 查询参数: {query_string}"
                
                # 根据状态码选择日志级别
                if status_code >= 500:
                    logger.error(log_message)
                elif status_code >= 400:
                    logger.warning(log_message)
                else:
                    logger.info(log_message)
            
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(RequestLogMiddleware)

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
app.include_router(proxy.router)
app.include_router(scrapers.router)


async def browser_idle_check():
    """后台任务：定期检查并关闭空闲浏览器实例，释放内存"""
    logger.info("Starting background browser idle check loop...")
    while True:
        try:
            # 检查 DrissionPage (同步方法在线程中运行)
            await asyncio.to_thread(drission_manager.check_idle, timeout=settings.browser_idle_timeout)
            
            # 检查 Playwright (异步方法)
            await browser_manager.check_idle_browser()
        except Exception as e:
            logger.error(f"Error in browser_idle_check: {e}")
        
        # 每 60 秒检查一次
        await asyncio.sleep(60)


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
    
    # 注册代理配置变更回调，用于动态更新定时任务
    proxy_service.register_config_callback(scheduler_service.refresh_system_jobs)
    
    # 启动定时任务调度器
    scheduler_service.start()
    
    # 启动站点采集定时任务调度器
    scraper_scheduler.start()
    
    # 启动浏览器空闲检查后台任务
    asyncio.create_task(browser_idle_check())


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
