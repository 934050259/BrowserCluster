"""
定时任务调度服务

使用 APScheduler 管理定时任务，根据配置的调度策略自动触发抓取任务
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.db.mongo import mongo
from app.models.schedule import ScheduleModel, ScheduleStatus, ScheduleType
from app.services.task_service import task_service
from app.models.task import ScrapeRequest

logger = logging.getLogger(__name__)

class SchedulerService:
    """定时任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler service started")
            # 从数据库加载所有激活的任务
            self._load_all_jobs()

    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler service stopped")

    def _load_all_jobs(self):
        """从数据库加载所有激活的定时任务并添加到调度器"""
        try:
            # 获取所有未删除且状态为激活的任务
            cursor = mongo.schedules.find({"status": ScheduleStatus.ACTIVE, "is_deleted": {"$ne": True}})
            schedules = list(cursor)
            for doc in schedules:
                self.add_job(ScheduleModel(**doc))
            logger.info(f"Loaded {len(schedules)} scheduled jobs from database")
        except Exception as e:
            logger.error(f"Failed to load scheduled jobs: {e}")

    async def _run_job(self, schedule_id: str, manual: bool = False):
        """执行定时任务：创建一个真实的抓取任务"""
        try:
            # 获取最新的调度配置
            doc = mongo.schedules.find_one({"schedule_id": schedule_id})
            if not doc:
                logger.warning(f"Schedule {schedule_id} not found, skipping execution")
                return
            
            # 如果不是手动触发，且状态不是激活，则跳过
            if not manual and doc.get("status") != ScheduleStatus.ACTIVE:
                logger.warning(f"Schedule {schedule_id} is inactive, skipping scheduled execution")
                return

            schedule = ScheduleModel(**doc)
            
            # 构造抓取请求
            request = ScrapeRequest(
                url=schedule.url,
                params=schedule.params,
                cache=schedule.cache,
                priority=schedule.priority,
                schedule_id=schedule_id
            )
            
            # 调用任务服务创建异步任务
            await task_service.create_task(request)
            
            # 更新最近运行时间
            mongo.schedules.update_one(
                {"schedule_id": schedule_id},
                {"$set": {"last_run": datetime.now()}}
            )
            logger.info(f"Scheduled job {schedule.name} ({schedule_id}) executed successfully")
            
        except Exception as e:
            logger.error(f"Error executing scheduled job {schedule_id}: {e}", exc_info=True)

    def add_job(self, schedule: ScheduleModel):
        """添加任务到调度器"""
        try:
            # 如果已存在同 ID 的任务，先删除
            if self.scheduler.get_job(schedule.schedule_id):
                self.scheduler.remove_job(schedule.schedule_id)

            trigger = None
            if schedule.schedule_type == ScheduleType.INTERVAL:
                trigger = IntervalTrigger(seconds=schedule.interval)
            elif schedule.schedule_type == ScheduleType.CRON:
                trigger = CronTrigger.from_crontab(schedule.cron)

            if trigger:
                self.scheduler.add_job(
                    self._run_job,
                    trigger=trigger,
                    args=[schedule.schedule_id],
                    id=schedule.schedule_id,
                    name=schedule.name,
                    replace_existing=True
                )
                logger.info(f"Added job to scheduler: {schedule.name} ({schedule_id=})")
        except Exception as e:
            logger.error(f"Failed to add job {schedule.schedule_id} to scheduler: {e}")

    def remove_job(self, schedule_id: str):
        """从调度器移除任务"""
        try:
            if self.scheduler.get_job(schedule_id):
                self.scheduler.remove_job(schedule_id)
                logger.info(f"Removed job from scheduler: {schedule_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {schedule_id} from scheduler: {e}")

    def pause_job(self, schedule_id: str):
        """暂停任务"""
        try:
            if self.scheduler.get_job(schedule_id):
                self.scheduler.pause_job(schedule_id)
                logger.info(f"Paused job in scheduler: {schedule_id}")
        except Exception as e:
            logger.error(f"Failed to pause job {schedule_id}: {e}")

    def resume_job(self, schedule_id: str):
        """恢复任务"""
        try:
            if self.scheduler.get_job(schedule_id):
                self.scheduler.resume_job(schedule_id)
                logger.info(f"Resumed job in scheduler: {schedule_id}")
            else:
                # 如果调度器中没有，可能是之前被暂停后状态变更，重新加载
                doc = mongo.db.schedules.find_one({"schedule_id": schedule_id})
                if doc:
                    self.add_job(ScheduleModel(**doc))
        except Exception as e:
            logger.error(f"Failed to resume job {schedule_id}: {e}")

# 全局单例
scheduler_service = SchedulerService()
