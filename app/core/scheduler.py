import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from app.db.mongo import mongo
from app.services.scraper_service import execute_scraper_task

logger = logging.getLogger(__name__)

class ScraperScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_jobs = {}  # scraper_id -> job_id

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scraper scheduler started")
            # 初始加载所有启用的定时任务
            asyncio.create_task(self.load_all_jobs())

    async def load_all_jobs(self):
        """从数据库加载所有启用的定时任务"""
        try:
            # 必须同时满足: 1. 站点已启用 (enabled); 2. 调度计划已开启 (enabled_schedule)
            enabled_scrapers = list(mongo.db.scrapers.find({
                "enabled": True,
                "enabled_schedule": True
            }))
            logger.info(f"Loading {len(enabled_scrapers)} active scraper schedules")
            for scraper in enabled_scrapers:
                self.add_or_update_job(scraper)
        except Exception as e:
            logger.error(f"Error loading scraper jobs: {e}")

    def add_or_update_job(self, scraper_doc: dict):
        """添加或更新定时任务"""
        scraper_id = str(scraper_doc["_id"])
        cron = scraper_doc.get("cron")
        
        # 必须同时满足站点启用和调度开启
        is_active = scraper_doc.get("enabled", True) and scraper_doc.get("enabled_schedule", False)

        # 如果任务已存在，先移除
        if scraper_id in self.running_jobs:
            try:
                self.scheduler.remove_job(self.running_jobs[scraper_id])
                del self.running_jobs[scraper_id]
                
                # 也要清除数据库里的 next_run_at
                mongo.db.scrapers.update_one(
                    {"_id": scraper_doc["_id"]},
                    {"$set": {"next_run_at": None}}
                )
            except:
                pass

        if is_active and cron:
            try:
                job = self.scheduler.add_job(
                    self._run_task,
                    CronTrigger.from_crontab(cron),
                    args=[scraper_id],
                    id=f"scraper_{scraper_id}",
                    replace_existing=True,
                    misfire_grace_time=60 # 超过 1 分钟则不再补偿执行
                )
                self.running_jobs[scraper_id] = job.id
                logger.info(f"Scheduled active scraper {scraper_id} with cron: {cron}")
                
                # 更新下一次运行时间
                next_run = job.next_run_time
                if next_run:
                    mongo.db.scrapers.update_one(
                        {"_id": scraper_doc["_id"]},
                        {"$set": {"next_run_at": next_run}}
                    )
            except Exception as e:
                logger.error(f"Failed to schedule scraper {scraper_id}: {e}")

    def remove_job(self, scraper_id: str):
        """移除定时任务"""
        if scraper_id in self.running_jobs:
            try:
                self.scheduler.remove_job(self.running_jobs[scraper_id])
                del self.running_jobs[scraper_id]
                logger.info(f"Removed scraper schedule: {scraper_id}")
                
                # 清除下一次运行时间
                mongo.db.scrapers.update_one(
                    {"_id": ObjectId(scraper_id)},
                    {"$set": {"next_run_at": None}}
                )
            except Exception as e:
                logger.error(f"Error removing scraper job {scraper_id}: {e}")

    async def _run_task(self, scraper_id: str):
        """执行定时任务"""
        try:
            scraper_doc = mongo.db.scrapers.find_one({"_id": ObjectId(scraper_id)})
            
            # 必须同时满足站点启用和调度开启
            is_active = scraper_doc and scraper_doc.get("enabled", True) and scraper_doc.get("enabled_schedule", False)
            
            if not is_active:
                self.remove_job(scraper_id)
                return

            logger.info(f"Executing scheduled scraper: {scraper_doc.get('name')} ({scraper_id})")
            
            # 更新最后运行时间
            now = datetime.now()
            mongo.db.scrapers.update_one(
                {"_id": ObjectId(scraper_id)},
                {"$set": {"last_run_at": now}}
            )

            # 调用已有的执行逻辑
            await execute_scraper_task(scraper_doc)
            
            # 更新下一次运行时间
            job = self.scheduler.get_job(f"scraper_{scraper_id}")
            if job:
                next_run = job.next_run_time
                if next_run:
                    mongo.db.scrapers.update_one(
                        {"_id": ObjectId(scraper_id)},
                        {"$set": {"next_run_at": next_run}}
                    )

        except Exception as e:
            logger.error(f"Error in scheduled task {scraper_id}: {e}")

# 单例模式
scraper_scheduler = ScraperScheduler()
