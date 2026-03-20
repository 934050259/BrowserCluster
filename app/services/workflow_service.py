import logging
import asyncio
from datetime import datetime
from bson import ObjectId
from app.db.mongo import mongo
from app.models.workflow import WorkflowBase
from app.services.workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)

async def execute_workflow_task(workflow_id: str, mode: str = "prod"):
    """执行定时工作流任务的具体逻辑"""
    try:
        workflow_doc = mongo.db.workflows.find_one({"_id": ObjectId(workflow_id)})
        if not workflow_doc:
            logger.error(f"Scheduled workflow {workflow_id} not found")
            return
            
        if not workflow_doc.get("is_active", True):
            logger.info(f"Workflow {workflow_id} is inactive, skipping scheduled execution")
            return

        # 创建执行记录用于追踪进度
        execution_record = {
            "workflow_id": ObjectId(workflow_id),
            "mode": mode,
            "status": "starting",
            "completed_nodes": 0,
            "total_nodes": len(workflow_doc.get("nodes", [])),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "trigger_type": "scheduled"
        }
        execution_result = mongo.db.workflow_executions.insert_one(execution_record)
        execution_id = str(execution_result.inserted_id)
        
        workflow = WorkflowBase(**workflow_doc)
        executor = WorkflowExecutor(workflow, workflow_id, mode=mode, execution_id=execution_id)
        
        # 执行工作流
        await executor.run()
        
        logger.info(f"Scheduled workflow {workflow_id} executed successfully (Execution ID: {execution_id})")
        
    except Exception as e:
        logger.error(f"Error executing scheduled workflow {workflow_id}: {e}", exc_info=True)
