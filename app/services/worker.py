"""
Worker 工作进程模块

从消息队列消费任务并执行网页抓取
"""
import asyncio
import logging
from datetime import datetime
from urllib.parse import urlparse
from app.services.queue_service import rabbitmq_service
from app.services.cache_service import cache_service
from app.core.scraper import scraper
from app.services.parser_service import parser_service
from app.core.config import settings
from app.db.mongo import mongo
from app.db.redis import redis_client
from app.core.browser import browser_manager

logger = logging.getLogger(__name__)


class Worker:
    """Worker 工作进程类"""

    def __init__(self, node_id: str = None):
        """
        初始化 Worker

        Args:
            node_id: 节点 ID，如果不指定则使用配置中的默认值
        """
        self.node_id = node_id or settings.node_id
        self.is_running = False  # 运行状态标志
        self.active_tasks = set()  # 当前正在处理的任务 ID 集合

    async def process_task(self, task_data: dict):
        """
        处理单个任务

        Args:
            task_data: 任务数据字典
        """
        # 提取任务信息
        task_id = task_data.get("task_id")
        url = task_data.get("url")
        params = task_data.get("params", {})

        if not task_id:
            return

        # 动态重载配置，确保使用最新的 LLM 等设置
        try:
            settings.load_from_db()
        except Exception as e:
            logger.warning(f"Failed to reload settings from DB: {e}")

        # 检查是否需要自动解析（如果任务没有明确指定解析器）
        if not params.get("parser"):
            domain = urlparse(url).netloc
            rule = mongo.parsing_rules.find_one({"domain": domain, "is_active": True})
            if rule:
                logger.info(f"Found matching parsing rule for domain {domain}: {rule['parser_type']}")
                params["parser"] = rule["parser_type"]
                params["parser_config"] = rule["parser_config"]

        logger.info(f"Processing task {task_id}: {url}")
        
        # 检查任务是否仍然存在于数据库中（可能已被删除）
        task = mongo.tasks.find_one({"task_id": task_id})
        if not task:
            logger.warning(f"Task {task_id} not found in database, it may have been deleted. Skipping.")
            return

        self.active_tasks.add(task_id)

        try:
            # 更新任务状态为处理中
            await self._update_task_status(task_id, "processing", self.node_id)

            # 执行抓取
            result = await scraper.scrape(url, params, self.node_id)

            # 如果抓取成功且配置了解析服务，执行解析
            if result["status"] == "success" and params.get("parser"):
                parser_type = params["parser"]
                parser_config = params.get("parser_config", {})
                html = result.get("html", "")
                
                logger.info(f"Parsing content for task {task_id} using {parser_type}")
                parsed_data = await parser_service.parse(html, parser_type, parser_config)
                result["parsed_data"] = parsed_data

            # 检查 Worker 是否在执行过程中被停止
            if not self.is_running:
                logger.warning(f"Worker stopped during task {task_id}, result will be ignored")
                return

            # 处理抓取结果
            if result["status"] == "success":
                # 更新任务状态为成功
                await self._update_task_success(task_id, result)

                # 如果启用缓存，则保存结果到缓存
                if task_data.get("cache", {}).get("enabled"):
                    # 构造缓存数据，包含状态和结果，与数据库结构保持一致
                    cache_data = {
                        "status": "success",
                        "result": result,
                        "completed_at": datetime.now().isoformat()
                    }
                    await cache_service.set(
                        url,
                        params,
                        cache_data,
                        task_data["cache"].get("ttl"),
                        task_id=task_id
                    )

                logger.info(f"Task {task_id} completed successfully")
            else:
                # 更新任务状态为失败
                await self._update_task_failed(task_id, result["error"])
                logger.error(f"Task {task_id} failed: {result['error']}")

        except Exception as e:
            # 处理异常
            if self.is_running:
                await self._update_task_failed(task_id, {"message": str(e)})
            logger.error(f"Task {task_id} error: {e}", exc_info=True)
        finally:
            self.active_tasks.discard(task_id)

    async def _update_task_status(self, task_id: str, status: str, node_id: str = None):
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 任务状态
            node_id: 处理节点 ID
        """
        mongo.tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": status,
                    "node_id": node_id,
                    "updated_at": datetime.now()
                }
            }
        )

    async def _update_task_success(self, task_id: str, result: dict):
        """
        更新任务为成功状态

        Args:
            task_id: 任务 ID
            result: 抓取结果
        """
        mongo.tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": "success",
                    "result": result,
                    "updated_at": datetime.now(),
                    "completed_at": datetime.now()
                }
            }
        )

    async def _update_task_failed(self, task_id: str, error: dict):
        """
        更新任务为失败状态

        Args:
            task_id: 任务 ID
            error: 错误信息
        """
        mongo.tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": "failed",
                    "error": error,
                    "updated_at": datetime.now(),
                    "completed_at": datetime.now()
                }
            }
        )

    async def run(self):
        """
        启动 Worker，开始消费任务
        """
        self.is_running = True
        logger.info(f"Worker {self.node_id} started")

        # 初始化时加载配置
        try:
            settings.load_from_db()
        except Exception as e:
            logger.warning(f"Initial settings reload failed: {e}")

        # 启动心跳循环
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # 启动浏览器空闲检查循环
        idle_check_task = asyncio.create_task(self._browser_idle_check_loop())

        # 预先启动浏览器
        await browser_manager.get_browser()

        try:
            loop = asyncio.get_event_loop()

            # 定义消息队列的回调函数
            def callback(task_data):
                asyncio.run_coroutine_threadsafe(
                    self.process_task(task_data),
                    loop
                )

            # 在线程池中运行阻塞式的消息队列消费
            await loop.run_in_executor(
                None,
                lambda: rabbitmq_service.consume_tasks(
                    callback,
                    prefetch_count=settings.worker_concurrency,
                    should_stop=lambda: not self.is_running
                )
            )

        except KeyboardInterrupt:
            logger.info("Worker stopping...")
        finally:
            heartbeat_task.cancel()
            idle_check_task.cancel()
            await self.stop()

    async def _browser_idle_check_loop(self):
        """
        周期性检查浏览器是否空闲，关闭长时间空闲的浏览器以释放内存
        """
        logger.info(f"Browser idle check loop started for {self.node_id}")
        while self.is_running:
            try:
                await browser_manager.check_idle_browser()
            except Exception as e:
                logger.error(f"Error checking idle browser: {e}")
            
            # 每 30 秒检查一次
            for _ in range(30):
                if not self.is_running:
                    break
                await asyncio.sleep(1)
        logger.info(f"Browser idle check loop stopped for {self.node_id}")

    async def _heartbeat_loop(self):
        """周期性更新节点心跳状态"""
        logger.info(f"Heartbeat loop started for {self.node_id}")
        while self.is_running:
            try:
                # 检查是否应该退出
                if not self.is_running:
                    break
                    
                mongo.nodes.update_one(
                    {"node_id": self.node_id},
                    {"$set": {"last_seen": datetime.now(), "status": "running"}}
                )
            except Exception as e:
                logger.error(f"Heartbeat error for {self.node_id}: {e}")
            
            # 分段睡眠，每秒检查一次 is_running 标志
            for _ in range(settings.heartbeat_interval):
                if not self.is_running:
                    break
                await asyncio.sleep(1)
        logger.info(f"Heartbeat loop stopped for {self.node_id}")

    async def stop(self):
        """
        停止 Worker，清理资源
        """
        self.is_running = False
        logger.info(f"Worker {self.node_id} stopping...")

        # 处理正在执行的任务
        if self.active_tasks:
            task_ids = list(self.active_tasks)
            logger.info(f"Worker {self.node_id} has {len(task_ids)} active tasks. Resetting status...")
            try:
                mongo.tasks.update_many(
                    {"task_id": {"$in": task_ids}},
                    {
                        "$set": {
                            "status": "pending",
                            "node_id": None,
                            "updated_at": datetime.now(),
                            "error": {"message": "Node stopped during processing"}
                        }
                    }
                )
                logger.info(f"Successfully reset {len(task_ids)} tasks to pending")
                self.active_tasks.clear()
            except Exception as e:
                logger.error(f"Error resetting active tasks: {e}")

        # 关闭本线程的浏览器和 Playwright 实例
        try:
            await browser_manager.close_playwright()
            logger.info(f"Worker {self.node_id} closed browser and Playwright")
        except Exception as e:
            logger.error(f"Error closing browser for {self.node_id}: {e}")

        try:
            mongo.nodes.update_one(
                {"node_id": self.node_id},
                {"$set": {"status": "stopped"}}
            )
        except Exception as e:
            logger.error(f"Error updating stop status for {self.node_id}: {e}")

        # 注意：在 API 服务器中运行时，不要关闭全局连接
        # rabbitmq_service.close()
        # await browser_manager.close_browser()
        # mongo.close()
        # redis_client.close_all()

        logger.info(f"Worker {self.node_id} stopped")


async def start_worker():
    """启动 Worker 的入口函数"""
    worker = Worker()
    await worker.run()
