import sys
import asyncio

# Windows 平台下，Playwright 需要使用 ProactorEventLoopPolicy 才能正常启动子进程
# 必须在导入任何其他模块之前设置，以确保事件循环策略生效
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.api import scrape, tasks, stats, admin, nodes, auth, users, rules, schedules, proxy, scrapers, cookies, workflows
from app.db.mongo import mongo
from app.db.redis import redis_client
from app.core.config import settings
from app.core.logger import setup_logging
from app.services.node_manager import node_manager
from app.services.scheduler_service import scheduler_service
from app.services.proxy_service import proxy_service
from app.services.cookie_service import cookie_service
from app.core.scheduler import scraper_scheduler
from app.core.drission_browser import drission_manager
from app.core.browser import browser_manager

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

async def browser_idle_check():
    """后台任务：定期检查并关闭空闲浏览器实例，释放内存"""
    logger.info("Starting background browser idle check loop...")
    while True:
        try:
            await asyncio.to_thread(drission_manager.check_idle, timeout=settings.browser_idle_timeout)
            await browser_manager.check_idle_browser()
        except Exception as e:
            logger.error(f"Error in browser_idle_check: {e}")
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：初始化与清理"""
    # 诊断 Windows 兼容性
    loop = asyncio.get_running_loop()
    logger.info(f"Lifespan startup. Current event loop: {type(loop).__name__}")
    
    # 初始化资源
    settings.load_from_db()
    mongo.connect()
    redis_client.connect_cache()
    await node_manager.auto_start_nodes()
    
    proxy_service.register_config_callback(scheduler_service.refresh_system_jobs)
    cookie_service.register_config_callback(scheduler_service.refresh_system_jobs)
    
    scheduler_service.start()
    scraper_scheduler.start()
    
    # 启动后台任务
    idle_task = asyncio.create_task(browser_idle_check())
    
    yield
    
    # 清理资源
    logger.info("Lifespan shutdown. Cleaning up...")
    idle_task.cancel()
    scheduler_service.stop()
    mongo.close()
    redis_client.close_all()
    logger.info("Cleanup complete.")

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Playwright-based distributed browser cluster",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
class RequestLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        method = scope.get("method")
        path = scope.get("path")
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.time() - start_time
                logger.info(f"API访问日志 | {client_ip} | {method} {path} | {status_code} | {process_time:.3f}s")
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
app.include_router(cookies.router)
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])

# 挂载截图目录
os.makedirs("screenshots", exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

@app.get("/api")
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 静态资源处理
static_dir = "static"
if not os.path.exists(static_dir) and os.path.exists("admin/dist"):
    static_dir = "admin/dist"

if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "Not Found", "status": 404}
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # 在 Windows 上禁用 reload 以确保 ProactorEventLoop 能够正确生效
    is_windows = sys.platform == 'win32'
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug and not is_windows, # Windows 下强制禁用热重载
        loop="asyncio",
        workers=1
    )
