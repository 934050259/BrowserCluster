from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class NodeBase(BaseModel):
    node_id: str = Field(..., description="节点唯一ID")
    queue_name: str = Field("task_queue", description="监听的任务队列")
    max_concurrent: int = Field(1, description="最大并发数")

class NodeCreate(NodeBase):
    pass

class NodeUpdate(BaseModel):
    queue_name: Optional[str] = None
    max_concurrent: Optional[int] = None
    status: Optional[str] = None

class NodeResponse(NodeBase):
    status: str = Field("stopped", description="状态: running, stopped, offline")
    task_count: int = Field(0, description="执行的任务总数")
    created_at: datetime
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True
