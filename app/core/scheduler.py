import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from app.db.mongo import mongo
from app.services.scraper_service import execute_scraper_task
from app.services.workflow_service import execute_workflow_task # 待会儿需要确保有这个函数

logger = logging.getLogger(__name__)

class UnifiedScheduler:
    def __init__(self):
        # 统一使用 Asia/Shanghai 时区，避免 8 小时时差问题
        self.scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')
        self.scraper_jobs = {}  # scraper_id -> job_id
        self.workflow_jobs = {} # workflow_id -> job_id

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Unified scheduler started")
            # 初始加载所有启用的定时任务
            asyncio.create_task(self.load_all_jobs())

    async def load_all_jobs(self):
        """从数据库加载所有启用的定时任务"""
        try:
            # 1. 加载站点采集任务
            enabled_scrapers = list(mongo.db.scrapers.find({
                "enabled": True,
                "enabled_schedule": True
            }))
            logger.info(f"Loading {len(enabled_scrapers)} active scraper schedules")
            for scraper in enabled_scrapers:
                self.add_or_update_scraper_job(scraper)
            
            # 2. 加载工作流任务
            enabled_workflows = list(mongo.db.workflows.find({
                "is_active": True,
                "schedule.is_enabled": True
            }))
            logger.info(f"Loading {len(enabled_workflows)} active workflow schedules")
            for workflow in enabled_workflows:
                self.add_or_update_workflow_job(workflow)
                
        except Exception as e:
            logger.error(f"Error loading scheduled jobs: {e}")

    # --- Scraper Jobs ---
    def add_or_update_scraper_job(self, scraper_doc: dict):
        scraper_id = str(scraper_doc["_id"])
        cron = scraper_doc.get("cron")
        is_active = scraper_doc.get("enabled", True) and scraper_doc.get("enabled_schedule", False)

        if scraper_id in self.scraper_jobs:
            try:
                self.scheduler.remove_job(self.scraper_jobs[scraper_id])
                del self.scraper_jobs[scraper_id]
                mongo.db.scrapers.update_one({"_id": scraper_doc["_id"]}, {"$set": {"next_run_at": None}})
            except: pass

        if is_active and cron:
            try:
                job = self.scheduler.add_job(
                    self._run_scraper_task,
                    CronTrigger.from_crontab(cron),
                    args=[scraper_id],
                    id=f"scraper_{scraper_id}",
                    replace_existing=True,
                    misfire_grace_time=60
                )
                self.scraper_jobs[scraper_id] = job.id
                next_run = job.next_run_time
                if next_run:
                    # 将时区感知的 datetime 转换为 naive datetime（本地时间），以匹配数据库中其他字段（如 updated_at）
                    next_run_local = next_run.replace(tzinfo=None)
                    mongo.db.scrapers.update_one({"_id": scraper_doc["_id"]}, {"$set": {"next_run_at": next_run_local}})
            except Exception as e:
                logger.error(f"Failed to schedule scraper {scraper_id}: {e}")

    async def _run_scraper_task(self, scraper_id: str):
        try:
            scraper_doc = mongo.db.scrapers.find_one({"_id": ObjectId(scraper_id)})
            if not scraper_doc or not (scraper_doc.get("enabled", True) and scraper_doc.get("enabled_schedule", False)):
                return
            await execute_scraper_task(scraper_doc)
            # Update next_run_at
            job = self.scheduler.get_job(f"scraper_{scraper_id}")
            if job:
                # 统一使用本地时间存储
                next_run_local = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
                mongo.db.scrapers.update_one({"_id": ObjectId(scraper_id)}, {"$set": {"next_run_at": next_run_local, "last_run_at": datetime.now()}})
        except Exception as e:
            logger.error(f"Error in scheduled scraper {scraper_id}: {e}")

    # --- Workflow Jobs ---
    def add_or_update_workflow_job(self, workflow_doc: dict):
        workflow_id = str(workflow_doc["_id"])
        sched = workflow_doc.get("schedule", {})
        is_enabled = sched.get("is_enabled", False) and workflow_doc.get("is_active", True)
        sched_type = sched.get("type", "none")
        sched_value = sched.get("value", "")

        if workflow_id in self.workflow_jobs:
            try:
                self.scheduler.remove_job(self.workflow_jobs[workflow_id])
                del self.workflow_jobs[workflow_id]
                mongo.db.workflows.update_one({"_id": workflow_doc["_id"]}, {"$set": {"next_run_at": None}})
            except: pass

        if is_enabled and sched_type != "none" and sched_value:
            try:
                trigger = None
                if sched_type == "interval":
                    try:
                        from apscheduler.triggers.interval import IntervalTrigger
                        seconds = int(sched_value)
                        if seconds < 10: seconds = 10 # 最小 10 秒
                        trigger = IntervalTrigger(seconds=seconds, timezone='Asia/Shanghai')
                    except ValueError:
                        logger.error(f"Invalid interval value for workflow {workflow_id}: {sched_value}")
                elif sched_type == "cron":
                    try:
                        trigger = CronTrigger.from_crontab(sched_value, timezone='Asia/Shanghai')
                    except Exception as e:
                        logger.error(f"Invalid cron expression for workflow {workflow_id}: {sched_value}, error: {e}")
                
                if trigger:
                    job = self.scheduler.add_job(
                        self._run_workflow_task,
                        trigger,
                        args=[workflow_id],
                        id=f"workflow_{workflow_id}",
                        replace_existing=True,
                        misfire_grace_time=60
                    )
                    self.workflow_jobs[workflow_id] = job.id
                    if job.next_run_time:
                        next_run_local = job.next_run_time.replace(tzinfo=None)
                        mongo.db.workflows.update_one({"_id": workflow_doc["_id"]}, {"$set": {"next_run_at": next_run_local}})
            except Exception as e:
                logger.error(f"Failed to schedule workflow {workflow_id}: {e}")

    async def _run_workflow_task(self, workflow_id: str):
        try:
            workflow_doc = mongo.db.workflows.find_one({"_id": ObjectId(workflow_id)})
            if not workflow_doc or not (workflow_doc.get("schedule", {}).get("is_enabled", False) and workflow_doc.get("is_active", True)):
                return
            
            logger.info(f"Executing scheduled workflow: {workflow_doc.get('name')} ({workflow_id})")
            await execute_workflow_task(workflow_id) # 会调用 WorkflowExecutor
            
            # Update next_run_at
            job = self.scheduler.get_job(f"workflow_{workflow_id}")
            if job:
                # 统一使用本地时间存储
                next_run_local = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
                mongo.db.workflows.update_one({"_id": ObjectId(workflow_id)}, {"$set": {"next_run_at": next_run_local, "last_run_at": datetime.now()}})
        except Exception as e:
            logger.error(f"Error in scheduled workflow {workflow_id}: {e}")

    def remove_workflow_job(self, workflow_id: str):
        """移除工作流定时任务"""
        if workflow_id in self.workflow_jobs:
            try:
                self.scheduler.remove_job(self.workflow_jobs[workflow_id])
                del self.workflow_jobs[workflow_id]
                logger.info(f"Removed workflow schedule: {workflow_id}")
                
                # 清除下一次运行时间
                mongo.db.workflows.update_one(
                    {"_id": ObjectId(workflow_id)},
                    {"$set": {"next_run_at": None}}
                )
            except Exception as e:
                logger.error(f"Error removing workflow job {workflow_id}: {e}")

# 单例
scheduler = UnifiedScheduler()
# 保持兼容性
scraper_scheduler = scheduler
