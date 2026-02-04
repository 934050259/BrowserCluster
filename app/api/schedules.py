"""
定时任务管理 API
"""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from app.db.mongo import mongo
from app.models.schedule import ScheduleModel, ScheduleCreate, ScheduleUpdate, ScheduleStatus
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/v1/schedules", tags=["定时任务"])

@router.post("/", response_model=ScheduleModel)
async def create_schedule(schedule_in: ScheduleCreate):
    """创建定时任务"""
    schedule_id = str(uuid.uuid4())
    now = datetime.now()
    
    schedule_data = schedule_in.dict()
    schedule_data.update({
        "schedule_id": schedule_id,
        "status": ScheduleStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
        "is_deleted": False
    })
    
    # 转换为模型以验证数据
    schedule = ScheduleModel(**schedule_data)
    
    # 保存到数据库 (将 HttpUrl 转换为字符串以兼容 MongoDB)
    data = schedule.dict()
    if data.get("url"):
        data["url"] = str(data["url"])
    mongo.schedules.insert_one(data)
    
    # 添加到调度器
    scheduler_service.add_job(schedule)
    
    return schedule

@router.get("/", response_model=dict)
async def list_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    name: Optional[str] = None
):
    """获取定时任务列表"""
    query = {"is_deleted": {"$ne": True}}
    if status and status.strip():
        query["status"] = status
    if name and name.strip():
        query["name"] = {"$regex": name, "$options": "i"}
        
    total = mongo.schedules.count_documents(query)
    cursor = mongo.schedules.find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    schedules = []
    for doc in cursor:
        # 获取下一次运行时间（从调度器中获取更准确）
        schedule = ScheduleModel(**doc)
        job = scheduler_service.scheduler.get_job(schedule.schedule_id)
        if job and job.next_run_time:
            schedule.next_run = job.next_run_time
        schedules.append(schedule)
        
    return {
        "total": total,
        "schedules": schedules
    }

@router.get("/{schedule_id}", response_model=ScheduleModel)
async def get_schedule(schedule_id: str):
    """获取单个定时任务详情"""
    doc = mongo.schedules.find_one({"schedule_id": schedule_id, "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    schedule = ScheduleModel(**doc)
    job = scheduler_service.scheduler.get_job(schedule_id)
    if job and job.next_run_time:
        schedule.next_run = job.next_run_time
        
    return schedule

@router.put("/{schedule_id}", response_model=ScheduleModel)
async def update_schedule(schedule_id: str, schedule_in: ScheduleUpdate):
    """更新定时任务"""
    doc = mongo.schedules.find_one({"schedule_id": schedule_id, "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    update_data = schedule_in.dict(exclude_unset=True)
    if update_data.get("url"):
        update_data["url"] = str(update_data["url"])
    update_data["updated_at"] = datetime.now()
    
    mongo.schedules.update_one(
        {"schedule_id": schedule_id},
        {"$set": update_data}
    )
    
    # 获取更新后的完整数据
    updated_doc = mongo.schedules.find_one({"schedule_id": schedule_id})
    schedule = ScheduleModel(**updated_doc)
    
    # 同步更新调度器
    if schedule.status == ScheduleStatus.ACTIVE:
        scheduler_service.add_job(schedule)
    else:
        scheduler_service.remove_job(schedule_id)
        
    return schedule

@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """删除定时任务"""
    result = mongo.schedules.update_one(
        {"schedule_id": schedule_id},
        {"$set": {"is_deleted": True, "status": ScheduleStatus.PAUSED, "updated_at": datetime.now()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    # 从调度器移除
    scheduler_service.remove_job(schedule_id)
    
    return {"message": "删除成功"}

@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    """切换任务状态（激活/暂停）"""
    doc = mongo.schedules.find_one({"schedule_id": schedule_id, "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    new_status = ScheduleStatus.PAUSED if doc["status"] == ScheduleStatus.ACTIVE else ScheduleStatus.ACTIVE
    
    mongo.schedules.update_one(
        {"schedule_id": schedule_id},
        {"$set": {"status": new_status, "updated_at": datetime.now()}}
    )
    
    if new_status == ScheduleStatus.ACTIVE:
        updated_doc = mongo.schedules.find_one({"schedule_id": schedule_id})
        scheduler_service.add_job(ScheduleModel(**updated_doc))
    else:
        scheduler_service.remove_job(schedule_id)
        
    return {"status": new_status}

@router.post("/{schedule_id}/run")
async def run_schedule_now(schedule_id: str):
    """立即执行一次定时任务"""
    doc = mongo.schedules.find_one({"schedule_id": schedule_id, "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    # 在后台执行，不阻塞 API
    import asyncio
    asyncio.create_task(scheduler_service._run_job(schedule_id, manual=True))
    
    return {"message": "已提交执行请求"}
