"""
任务管理 API 路由模块

提供任务查询、列表、删除等功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from app.models.task import TaskResponse, BatchDeleteRequest
from app.db.mongo import mongo
from app.services.queue_service import rabbitmq_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.delete("/batch")
async def batch_delete_tasks(request: BatchDeleteRequest, current_user: dict = Depends(get_current_user)):
    """
    批量删除任务

    Args:
        request: 包含任务 ID 列表的请求

    Returns:
        dict: 删除结果
    """
    result = mongo.tasks.delete_many({"task_id": {"$in": request.task_ids}})
    return {
        "status": "success",
        "message": f"Successfully deleted {result.deleted_count} tasks",
        "deleted_count": result.deleted_count
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str, 
    include_html: bool = Query(True, description="是否包含 HTML 源码"),
    include_screenshot: bool = Query(True, description="是否包含截图数据"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取单个任务详情

    Args:
        task_id: 任务 ID
        include_html: 是否在结果中包含完整的 HTML 源码 (数据量大时建议关闭)
        include_screenshot: 是否在结果中包含截图 Base64 (数据量大时建议关闭)

    Returns:
        TaskResponse: 任务详细信息
    """
    # 构建投影，默认排除大数据字段
    projection = {}
    if not include_html:
        projection["result.html"] = 0
    if not include_screenshot:
        projection["result.screenshot"] = 0

    task = mongo.tasks.find_one({"task_id": task_id}, projection)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        task_id=task["task_id"],
        url=task["url"],
        node_id=task.get("node_id"),
        status=task["status"],
        params=task.get("params"),
        priority=task.get("priority"),
        cache=task.get("cache"),
        result=task.get("result"),
        error=task.get("error"),
        cached=task.get("cached", False),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        completed_at=task.get("completed_at")
    )


@router.get("/")
async def list_tasks(
    status: str = None,
    url: str = None,
    schedule_id: str = None,
    cached: bool = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    获取任务列表

    Args:
        status: 任务状态过滤（可选）
        url: 目标 URL 搜索（可选，模糊匹配）
        cached: 是否命中缓存过滤（可选）
        skip: 跳过的记录数
        limit: 返回的记录数

    Returns:
        dict: 包含总数和任务列表的字典
    """
    # 构建查询条件
    query = {}
    if status:
        query["status"] = status
    if schedule_id:
        query["schedule_id"] = schedule_id
    if url:
        query["$or"] = [
            {"url": {"$regex": url, "$options": "i"}},
            {"task_id": {"$regex": url, "$options": "i"}}
        ]
    if cached is not None:
        query["cached"] = cached

    # 查询任务列表，只返回指定字段
    projection = {
            "task_id": 1,
            "url": 1,
            "params": 1,
            "priority": 1,
            "cache": 1,
            "status": 1,
            "cached": 1,
            "node_id": 1,
            "created_at": 1,
            "updated_at": 1,
            "completed_at": 1,
            "result.metadata.load_time": 1
        }
    tasks = mongo.tasks.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)

    return {
        "total": mongo.tasks.count_documents(query),
        "tasks": [
            {
                "task_id": task["task_id"],
                "url": task["url"],
                "params": task.get("params", {}),
                "priority": task.get("priority", 1),
                "cache": task.get("cache", {"enabled": True, "ttl": 3600}),
                "status": task["status"],
                "cached": task.get("cached", False),
                "node_id": task.get("node_id"),
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "completed_at": task.get("completed_at"),
                "duration": task.get("result", {}).get("metadata", {}).get("load_time")
            }
            for task in tasks
        ]
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务

    Args:
        task_id: 任务 ID

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 任务不存在时返回 404
    """
    result = mongo.tasks.delete_one({"task_id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "message": "Task deleted"}


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str):
    """
    重试任务

    Args:
        task_id: 任务 ID

    Returns:
        TaskResponse: 更新后的任务信息

    Raises:
        HTTPException: 任务不存在或重入队失败
    """
    # 1. 查找现有任务
    task = mongo.tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. 更新任务状态为 pending，并清除之前的错误和结果
    now = datetime.now()
    update_data = {
        "status": "pending",
        "error": None,
        "result": None,
        "cached": False,
        "updated_at": now,
        "completed_at": None,
        "node_id": None
    }

    mongo.tasks.update_one({"task_id": task_id}, {"$set": update_data})

    # 3. 重新提交到队列
    queue_task = {
        "task_id": task_id,
        "url": task["url"],
        "params": task["params"],
        "cache": task.get("cache", {"enabled": True, "ttl": 3600}),
        "priority": task.get("priority", 1)
    }

    if not rabbitmq_service.publish_task(queue_task):
        # 如果发布失败，尝试将状态改回失败（但不抛出异常，因为状态更新本身可能失败）
        mongo.tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": "failed", "error": {"message": "Failed to re-queue task"}}}
        )
        raise HTTPException(status_code=500, detail="Failed to queue task")

    # 4. 返回更新后的任务信息
    return TaskResponse(
        task_id=task_id,
        url=task["url"],
        status="pending",
        created_at=task["created_at"],
        updated_at=now
    )
