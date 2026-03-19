from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from app.models.common import PyObjectId
from bson import ObjectId

class NodeType(str, Enum):
    START = "start"
    GOTO = "goto"
    CLICK = "click"
    TYPE = "type"
    WAIT = "wait"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    GET_INFO = "get_info"
    IF = "if"
    LOOP = "loop"
    TAB_SWITCH = "tab_switch"
    IFRAME_SWITCH = "iframe_switch"
    HOVER = "hover"
    KEYPRESS = "keypress"
    END = "end"

class WorkflowNode(BaseModel):
    id: str
    type: NodeType
    label: str
    params: Dict[str, Any] = Field(default_factory=dict)
    # 针对分支节点的逻辑
    conditions: Optional[List[Dict[str, Any]]] = None
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    # 针对分支节点的边
    condition_index: Optional[int] = None

class WorkflowBase(BaseModel):
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="描述")
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict, description="全局变量/环境配置")
    is_active: bool = Field(True, description="是否启用")

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[WorkflowNode]] = None
    edges: Optional[List[WorkflowEdge]] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

from pydantic import BaseModel, Field, ConfigDict

class WorkflowResponse(WorkflowBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
