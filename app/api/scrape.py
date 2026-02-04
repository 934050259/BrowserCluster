"""
网页抓取 API 路由模块

提供同步/异步/批量抓取网页的 API 接口
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
from app.models.task import (
    ScrapeRequest,
    TaskResponse,
    BatchScrapeRequest,
    BatchScrapeResponse
)
from app.services.queue_service import rabbitmq_service
from app.services.cache_service import cache_service
from app.services.task_service import task_service
from app.db.mongo import mongo
from app.core.config import settings
from app.core.auth import get_current_user
import asyncio

router = APIRouter(prefix="/api/v1/scrape", tags=["Scrape"])


@router.post("/", response_model=TaskResponse)
async def scrape(request: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    """
    同步抓取网页

    1. 优先检查缓存：若缓存命中，直接返回缓存结果，并在数据库中记录一条“已缓存”任务记录，方便用户查看历史。
    2. 缓存未命中：创建新任务并提交到 RabbitMQ，随后轮询数据库等待任务完成（默认超时 30 秒）。
    3. 任务完成或失败后，立即返回最终状态及结果；超时则抛出 504 异常。

    Args:
        request: 抓取请求，包含目标 URL、参数、优先级、缓存策略等。

    Returns:
        TaskResponse: 包含任务 ID、状态、结果/错误、是否命中缓存、各时间节点等信息。
    """
    url = str(request.url)
    params = request.params.model_dump()
    task_id = str(ObjectId())

    # 生成缓存键
    cache_key = cache_service.generate_cache_key(url, params)

    # 如果启用缓存，尝试从缓存获取
    if request.cache.enabled:
        cached = await cache_service.get(url, params)
        if cached:
            # 处理缓存数据结构：老版本缓存可能直接存储 result，新版本可能包含 status 和 result 包装
            result_data = cached.get("result") if "result" in cached else cached
            
            # 处理完成时间：优先使用包装层的时间，否则尝试从 metadata 中获取
            completed_at = cached.get("completed_at")
            if not completed_at and isinstance(result_data, dict):
                completed_at = result_data.get("metadata", {}).get("timestamp")
            
            # 即便是缓存命中，我们也记录一条任务记录到数据库，方便用户在列表中看到
            task_data = {
                "task_id": task_id,
                "url": url,
                "status": cached.get("status", "success"),
                "priority": request.priority,
                "params": params,
                "result": result_data,
                "cache_key": cache_key,
                "cached": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "completed_at": completed_at or datetime.now()
            }
            mongo.tasks.insert_one(task_data)

            return TaskResponse(
                task_id=task_id,
                url=url,
                status=task_data["status"],
                params=task_data["params"],
                priority=task_data["priority"],
                result=task_data["result"],
                cached=True,
                created_at=task_data["created_at"],
                updated_at=task_data["updated_at"],
                completed_at=task_data["completed_at"]
            )

    # 构建任务数据
    task_data = {
        "task_id": task_id,
        "url": url,
        "status": "pending",
        "priority": request.priority,
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
        raise HTTPException(status_code=500, detail="Failed to queue task")
    
    # 设置超时时间（默认 30 秒，或使用请求参数中的超时）
    timeout = request.params.timeout / 1000 if request.params.timeout else 30
    start_time = datetime.now()
    
    # 轮询检查间隔
    check_interval = 1
    
    try:
        while (datetime.now() - start_time).total_seconds() < timeout:
            # 检查任务状态
            task = mongo.tasks.find_one({"task_id": task_id})
            
            if task and task["status"] in ["success", "failed"]:
                return TaskResponse(
                    task_id=task_id,
                    url=url,
                    status=task["status"],
                    params=task.get("params"),
                    priority=task.get("priority"),
                    cache=task.get("cache"),
                    result=task.get("result"),
                    error=task.get("error"),
                    cached=False,
                    created_at=task["created_at"],
                    updated_at=task["updated_at"],
                    completed_at=task.get("completed_at")
                )
            
            # 等待下一次检查
            await asyncio.sleep(check_interval)
            
        # 超时处理
        raise HTTPException(status_code=504, detail="Task execution timed out")
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error waiting for task result: {str(e)}")


@router.post("/async", response_model=TaskResponse)
async def scrape_async(request: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    """
    异步抓取网页

    不检查缓存，直接创建新任务并提交到队列，立即返回任务信息。

    Args:
        request: 抓取请求

    Returns:
        TaskResponse: 任务响应信息
    """
    return await task_service.create_task(request)


@router.post("/batch", response_model=BatchScrapeResponse)
async def scrape_batch(request: BatchScrapeRequest, current_user: dict = Depends(get_current_user)):
    """
    批量抓取网页

    支持一次性提交多个抓取任务。
    批量接口目前仅支持异步模式，不直接返回抓取结果。

    Args:
        request: 批量抓取请求

    Returns:
        BatchScrapeResponse: 批量任务响应信息
    """
    task_ids = []

    # 遍历每个任务
    for req in request.tasks:
        url = str(req.url)
        params = req.params.model_dump()
        task_id = str(ObjectId())
        cache_key = cache_service.generate_cache_key(url, params)

        # 构建任务数据
        task_data = {
            "task_id": task_id,
            "url": url,
            "status": "pending",
            "priority": req.priority,
            "params": params,
            "cache": req.cache.model_dump(),
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
            "cache": req.cache.model_dump(),
            "priority": req.priority
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
        task_ids.append(task_id)

    return BatchScrapeResponse(task_ids=task_ids)
