from datetime import datetime
from bson import ObjectId
from app.models.task import ScrapeRequest, TaskResponse
from app.services.queue_service import rabbitmq_service
from app.services.cache_service import cache_service
from app.db.mongo import mongo

class TaskService:
    @staticmethod
    async def create_task(request: ScrapeRequest) -> TaskResponse:
        """
        创建并提交一个抓取任务
        """
        url = str(request.url)
        params = request.params.model_dump()

        # 生成任务 ID
        task_id = str(ObjectId())
        cache_key = cache_service.generate_cache_key(url, params)

        # 构建任务数据
        task_data = {
            "task_id": task_id,
            "url": url,
            "status": "pending",
            "priority": request.priority,
            "schedule_id": request.schedule_id,
            "params": params,
            "cache": request.cache.model_dump(),
            "cache_key": cache_key,
            "cached": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # 保存任务到数据库
        mongo.tasks.insert_one(task_data)

        # 构建队列任务
        queue_task = {
            "task_id": task_id,
            "url": url,
            "params": params,
            "cache": request.cache.model_dump(),
            "priority": request.priority
        }

        # 发布任务到队列
        if not rabbitmq_service.publish_task(queue_task):
            mongo.tasks.update_one(
                {"task_id": task_id},
                {"$set": {
                    "status": "failed",
                    "error": {"message": "Failed to queue task: RabbitMQ connection issue"},
                    "updated_at": datetime.now()
                }}
            )
        
        return TaskResponse(
            task_id=task_id,
            url=url,
            status="pending",
            params=params,
            priority=request.priority,
            cache=request.cache.model_dump(),
            created_at=task_data["created_at"],
            updated_at=task_data["updated_at"]
        )

task_service = TaskService()
