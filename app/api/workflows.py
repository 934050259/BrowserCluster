from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import logging
from bson import ObjectId
from datetime import datetime
from app.db.mongo import mongo
from app.models.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowBase
from app.services.workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=WorkflowResponse)
async def create_workflow(workflow: WorkflowCreate):
    workflow_dict = workflow.dict()
    workflow_dict["created_at"] = datetime.now()
    workflow_dict["updated_at"] = datetime.now()
    workflow_dict["next_run_at"] = None
    workflow_dict["last_run_at"] = None
    
    result = mongo.db.workflows.insert_one(workflow_dict)
    workflow_dict["_id"] = result.inserted_id
    return workflow_dict

@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows(skip: int = 0, limit: int = 1000):
    workflows = list(mongo.db.workflows.find().sort("updated_at", -1).skip(skip).limit(limit))
    return workflows

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    workflow = mongo.db.workflows.find_one({"_id": ObjectId(workflow_id)})
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

from pymongo import ReturnDocument
from app.core.scheduler import scheduler

@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, workflow_update: WorkflowUpdate):
    update_data = workflow_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    
    result = mongo.db.workflows.find_one_and_update(
        {"_id": ObjectId(workflow_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    # 同步定时任务到调度器
    scheduler.add_or_update_workflow_job(result)
    
    return result

@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    result = mongo.db.workflows.delete_one({"_id": ObjectId(workflow_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    # 从调度器中移除
    scheduler.remove_workflow_job(workflow_id)
    
    return {"message": "Workflow deleted"}

@router.post("/batch-delete")
async def batch_delete_workflows(workflow_ids: List[str]):
    object_ids = [ObjectId(wid) for wid in workflow_ids]
    result = mongo.db.workflows.delete_many({"_id": {"$in": object_ids}})
    return {"message": f"Deleted {result.deleted_count} workflows"}

@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, background_tasks: BackgroundTasks, mode: str = "prod"):
    if mode not in ["test", "prod"]:
        raise HTTPException(status_code=400, detail="Invalid execution mode")
        
    workflow_doc = mongo.db.workflows.find_one({"_id": ObjectId(workflow_id)})
    if not workflow_doc:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # 检查是否已有正在运行的任务
    active_execution = mongo.db.workflow_executions.find_one({
        "workflow_id": ObjectId(workflow_id),
        "status": {"$in": ["starting", "running"]}
    })
    if active_execution:
        raise HTTPException(
            status_code=409, 
            detail=f"Workflow is already running (Status: {active_execution['status']})"
        )
    
    # 如果是测试模式，清除之前的测试数据（日志、结果、执行记录）
    if mode == "test":
        # 彻底清除所有与此工作流相关的测试数据
        mongo.db.workflow_logs.delete_many({"workflow_id": ObjectId(workflow_id), "mode": "test"})
        mongo.db.workflow_test_results.delete_many({"workflow_id": ObjectId(workflow_id)})
        # 同时清除所有历史执行记录，无论状态（除了当前正在运行的，但前面已经检查过了）
        mongo.db.workflow_executions.delete_many({"workflow_id": ObjectId(workflow_id), "mode": "test"})
        logger.info(f"Cleared all test data for workflow {workflow_id}")
    
    # 创建执行记录用于追踪进度
    execution_record = {
        "workflow_id": ObjectId(workflow_id),
        "mode": mode,
        "status": "starting",
        "completed_nodes": 0,
        "total_nodes": len(workflow_doc.get("nodes", [])),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    execution_result = mongo.db.workflow_executions.insert_one(execution_record)
    execution_id = str(execution_result.inserted_id)
    
    workflow = WorkflowBase(**workflow_doc)
    executor = WorkflowExecutor(workflow, workflow_id, mode=mode, execution_id=execution_id)
    
    # 异步执行
    background_tasks.add_task(executor.run)
    
    return {
        "message": f"Workflow {mode} execution started", 
        "workflow_id": workflow_id, 
        "execution_id": execution_id,
        "mode": mode
    }

@router.get("/executions/active")
async def get_active_executions():
    active = list(mongo.db.workflow_executions.find({
        "status": {"$in": ["starting", "running"]}
    }))
    for ex in active:
        ex["_id"] = str(ex["_id"])
        ex["workflow_id"] = str(ex["workflow_id"])
        if "created_at" in ex:
            ex["created_at"] = ex["created_at"].isoformat()
        if "updated_at" in ex:
            ex["updated_at"] = ex["updated_at"].isoformat()
    return active

@router.get("/executions/{execution_id}/status")
async def get_execution_status(execution_id: str):
    execution = mongo.db.workflow_executions.find_one({"_id": ObjectId(execution_id)})
    if not execution:
        raise HTTPException(status_code=404, detail="Execution record not found")
    
    execution["_id"] = str(execution["_id"])
    execution["workflow_id"] = str(execution["workflow_id"])
    if "created_at" in execution:
        execution["created_at"] = execution["created_at"].isoformat()
    if "updated_at" in execution:
        execution["updated_at"] = execution["updated_at"].isoformat()
        
    return execution

@router.delete("/{workflow_id}/test-data")
async def clear_test_data(workflow_id: str):
    mongo.db.workflow_logs.delete_many({"workflow_id": ObjectId(workflow_id), "mode": "test"})
    mongo.db.workflow_test_results.delete_many({"workflow_id": ObjectId(workflow_id)})
    mongo.db.workflow_executions.delete_many({"workflow_id": ObjectId(workflow_id), "mode": "test"})
    return {"message": "Test data cleared"}

@router.get("/{workflow_id}/executions")
async def get_workflow_executions(workflow_id: str, mode: str = "prod", skip: int = 0, limit: int = 20):
    collection = mongo.db.workflow_results if mode == "prod" else mongo.db.workflow_test_results
    executions = list(collection.find({"workflow_id": ObjectId(workflow_id)})
                      .sort("timestamp", -1)
                      .skip(skip)
                      .limit(limit))
    for ex in executions:
        ex["_id"] = str(ex["_id"])
        ex["workflow_id"] = str(ex["workflow_id"])
        if "timestamp" in ex:
            ex["timestamp"] = ex["timestamp"].isoformat()
    return executions

@router.get("/{workflow_id}/logs")
async def get_workflow_logs(workflow_id: str, mode: Optional[str] = None):
    query = {"workflow_id": ObjectId(workflow_id)}
    if mode:
        query["mode"] = mode
        
    logs = list(mongo.db.workflow_logs.find(query).sort("timestamp", -1).limit(100))
    for log in logs:
        log["_id"] = str(log["_id"])
        log["workflow_id"] = str(log["workflow_id"])
        log["timestamp"] = log["timestamp"].isoformat()
    return {"logs": logs}
