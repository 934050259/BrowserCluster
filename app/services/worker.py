"""
Worker 工作进程模块

从消息队列消费任务并执行网页抓取
"""
import asyncio
import logging
import time
from datetime import datetime
from urllib.parse import urlparse
from app.services.queue_service import rabbitmq_service
from app.services.cache_service import cache_service
from app.core.scraper import scraper
from app.services.parser_service import parser_service
from app.services.oss_service import oss_service
from app.core.config import settings
from app.db.mongo import mongo
from app.core.browser import browser_manager
from app.core.drission_browser import drission_manager

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
        self.active_tasks = {}  # 当前正在处理的任务 ID -> 任务数据 映射

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

        # 检查是否匹配网站规则配置
        domain = urlparse(url).netloc
        # 获取匹配该域名的规则，按优先级排序
        rules = list(mongo.parsing_rules.find({"is_active": True}).sort("priority", -1))
        matched_rule = None
        
        for rule in rules:
            rule_domain = rule.get("domain", "")
            if rule_domain == domain:
                matched_rule = rule
                break
            if rule_domain.startswith("*."):
                suffix = rule_domain[1:] # .example.com
                if domain.endswith(suffix):
                    matched_rule = rule
                    break
        
        if matched_rule:
            logger.info(f"Applying rule settings for domain {domain} (Rule: {matched_rule['domain']})")
            # 1. 解析配置 (如果任务没有指定)
            if not params.get("parser"):
                params["parser"] = matched_rule.get("parser_type")
                params["parser_config"] = matched_rule.get("parser_config")
            
            # 2. 浏览器特征与高级配置 (如果任务参数中对应值为 None 或默认值，则应用规则)
            # 定义需要从规则中同步的字段
            sync_fields = [
                "engine", "wait_for", "timeout", "viewport", "stealth", 
                "save_html", "screenshot", "is_fullscreen", "block_images",
                "intercept_apis", "intercept_continue", "proxy",
                "storage_type", "mongo_collection", "oss_path"
            ]
            
            for field in sync_fields:
                # 如果任务 params 中没有该字段，或者该字段是空的/默认的，则使用规则配置
                # 注意：这里需要谨慎判断，避免覆盖用户在新建任务时明确设置的参数
                if field not in params or params[field] is None:
                    params[field] = matched_rule.get(field)
            
            # 3. Cookies (如果任务没有指定)
            if not params.get("cookies") and matched_rule.get("cookies"):
                params["cookies"] = matched_rule.get("cookies")

        logger.info(f"Processing task {task_id}: {url}")
        
        # 检查任务是否仍然存在于数据库中（可能已被删除）
        task = mongo.tasks.find_one({"task_id": task_id})
        if not task:
            logger.warning(f"Task {task_id} not found in database, it may have been deleted. Skipping.")
            return

        self.active_tasks[task_id] = task_data

        try:
            # 更新任务状态为处理中
            await self._update_task_status(task_id, "processing", self.node_id)

            # 执行抓取
            result = await scraper.scrape(url, params, self.node_id)

            # 如果抓取成功且配置了解析服务，执行解析
            if result["status"] == "success" and params.get("parser"):
                parser_type = params["parser"]
                parser_config = params.get("parser_config", {})
                
                # 即使 params["save_html"] 为 False，result["html"] 在 scraper 阶段也是存在的
                # scraper 保证了 result["html"] 包含内容，解析服务需要这个内容
                html_content = result.get("html", "")
                
                if not html_content:
                    logger.warning(f"Task {task_id} successful but HTML content is empty, parser might fail")
                
                logger.info(f"Parsing content for task {task_id} using {parser_type}")
                parsed_data = await parser_service.parse(html_content, parser_type, parser_config)
                result["parsed_data"] = parsed_data

            # 这里重新判断是否需要保存html
            result["html"] = result.get("html", "") if params.get("save_html", True) else ""

            # 检查 Worker 是否在执行过程中被停止
            if not self.is_running:
                logger.warning(f"Worker stopped during task {task_id}, result will be ignored")
                return

            # 处理抓取结果
            if result["status"] == "success":
                # 更新任务状态为成功
                await self._update_task_success(task_id, result, params)

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
            self.active_tasks.pop(task_id, None)

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
                },
                "$unset": {
                    "error": ""
                }
            }
        )

    async def _update_task_success(self, task_id: str, result: dict, params: dict = None):
        """
        更新任务为成功状态

        Args:
            task_id: 任务 ID
            result: 抓取结果
            params: 任务参数
        """
        # 处理存储逻辑
        if params:
            storage_type = params.get("storage_type", "mongo")
            save_html = params.get("save_html", True)
            oss_path = params.get("oss_path")
            mongo_collection = params.get("mongo_collection")
            
            # 如果不保存 HTML，从结果中移除
            if not save_html:
                result.pop("html", None)
            
            # 处理 OSS 存储
            if storage_type == "oss":
                html = result.get("html")
                screenshot = result.get("screenshot")
                
                # 上传到 OSS (如果显式指定了 OSS，则强制上传，忽略全局开关)
                html_url, screenshot_url = oss_service.upload_task_assets(task_id, html, screenshot, force=True, custom_path=oss_path)
                
                # 更新结果：OSS 存储时，移除原始 html/screenshot 字段，仅保留 oss_ 路径
                if html_url:
                    result["oss_html"] = html_url  # 显式保存 OSS 路径
                    result.pop("html", None)       # 移除原始字段
                
                if screenshot_url:
                    result["oss_screenshot"] = screenshot_url  # 显式保存 OSS 路径
                    result.pop("screenshot", None)             # 移除原始字段
                
                # 如果成功上传了任一资源，标记为 oss 存储
                if html_url or screenshot_url:
                    result["storage_type"] = "oss"
                else:
                    # 如果 OSS 上传失败且原本有数据，则保留原始数据（存入 Mongo）
                    # 这样可以防止数据丢失，同时在 UI 上显示为存入 Mongo
                    result["storage_type"] = "mongo"
                    logger.warning(f"OSS upload failed for task {task_id}, falling back to MongoDB storage")

            # 处理自定义 MongoDB 存储
            # 如果提供了 mongo_collection 或者明确指定了 storage_type 为 mongo
            if storage_type == "mongo":
                target_collection = (mongo_collection or "tasks_results").strip()
                try:
                    # 确保集合名称合法且不为系统集合
                    if target_collection and not target_collection.startswith("system."):
                        # 避免重复保存到主 tasks 集合 (如果 target_collection 就是 tasks)
                        if target_collection != "tasks":
                            mongo.db[target_collection].insert_one({
                                "task_id": task_id,
                                "url": result.get("metadata", {}).get("url") or task_id,
                                "result": result,
                                "timestamp": datetime.now()
                            })
                            logger.info(f"Task {task_id} result also saved to collection: {target_collection}")
                except Exception as e:
                    logger.error(f"Failed to save task {task_id} to collection {target_collection}: {e}")

        mongo.tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": "success",
                    "result": result,
                    "updated_at": datetime.now(),
                    "completed_at": datetime.now()
                },
                "$unset": {
                    "error": ""
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
            try:
                await asyncio.gather(heartbeat_task, idle_check_task, return_exceptions=True)
            except:
                pass
            await self.stop()

    async def _browser_idle_check_loop(self):
        """
        周期性检查浏览器是否空闲，关闭长时间空闲的浏览器以释放内存
        """
        logger.info(f"Browser idle check loop started for {self.node_id}")
        while self.is_running:
            try:
                # 检查 Playwright 浏览器
                await browser_manager.check_idle_browser()
                
                # 检查 DrissionPage 浏览器 (同步方法在线程中运行)
                await asyncio.to_thread(self._check_drission_idle)
            except Exception as e:
                logger.error(f"Error checking idle browser: {e}")
            
            # 每 30 秒检查一次
            for _ in range(30):
                if not self.is_running:
                    break
                await asyncio.sleep(1)
        logger.info(f"Browser idle check loop stopped for {self.node_id}")

    def _check_drission_idle(self):
        """检查并清理空闲的 DrissionPage 实例"""
        try:
            # 如果浏览器本身就没打开，直接返回
            if not drission_manager.is_active:
                return

            idle_timeout = settings.browser_idle_timeout # 使用配置的超时时间
            current_time = time.time()
            last_used = drission_manager.last_used_time
            
            if last_used > 0 and (current_time - last_used) > idle_timeout:
                logger.info(f"DrissionPage idle for {int(current_time - last_used)}s, closing...")
                drission_manager.close_browser()
        except Exception as e:
            logger.error(f"Error in _check_drission_idle: {e}")

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

        # 立即处理正在执行的任务，将其重置为待处理状态，并重新发布到消息队列
        if self.active_tasks:
            task_items = list(self.active_tasks.items())
            task_ids = [item[0] for item in task_items]
            logger.info(f"Worker {self.node_id} has {len(task_ids)} active tasks. Resetting status and republishing...")
            try:
                # 1. 更新数据库状态为 pending
                mongo.tasks.update_many(
                    {"task_id": {"$in": task_ids}},
                    {
                        "$set": {
                            "status": "pending",
                            "node_id": None,
                            "updated_at": datetime.now()
                        },
                        "$unset": {
                            "error": ""
                        }
                    }
                )
                
                # 2. 重新发布任务消息到 RabbitMQ
                for task_id, task_data in task_items:
                    success = rabbitmq_service.publish_task(task_data)
                    if success:
                        logger.info(f"Task {task_id} successfully republished to RabbitMQ")
                    else:
                        logger.error(f"Failed to republish task {task_id} to RabbitMQ")

                logger.info(f"Successfully processed {len(task_ids)} tasks for rollback")
                # 不主动清空 active_tasks，由各协程的 finally 块自行清理，
                # 但由于 is_running 已为 False，后续的数据库更新操作会被跳过
            except Exception as e:
                logger.error(f"Error during tasks rollback: {e}")

        # 关闭本线程的浏览器和 Playwright 实例
        try:
            await browser_manager.close_playwright()
            # 同时也关闭 DrissionPage 实例
            await asyncio.to_thread(drission_manager.close_browser)
            logger.info(f"Worker {self.node_id} closed browser and Playwright/DrissionPage")
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
