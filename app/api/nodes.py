from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
import os
import asyncio
from app.models.node import NodeCreate, NodeResponse, NodeUpdate
from app.services.node_manager import node_manager
from app.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes"])

@router.get("/{node_id}/logs")
async def get_node_logs(
    node_id: str, 
    lines: int = Query(100, ge=1, le=1000),
    stream: bool = Query(False),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取节点运行日志
    
    Args:
        node_id: 节点 ID
        lines: 返回最后多少行日志
        stream: 是否实时流式输出
    """
    log_file = f"logs/node-{node_id}.log"
    
    if not os.path.exists(log_file):
        # 如果是正在运行的节点但还没日志文件，可能还没产生日志
        if node_id in node_manager.active_workers:
            return StreamingResponse(iter(["Waiting for logs..."]), media_type="text/plain")
        raise HTTPException(status_code=404, detail="Log file not found for this node")

    def read_last_lines(file_path, n):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 简单实现：读取所有行并取最后 n 行
            # 对于 5MB 的文件，性能还可以
            all_lines = f.readlines()
            return all_lines[-n:]

    if not stream:
        content = "".join(read_last_lines(log_file, lines))
        return StreamingResponse(iter([content]), media_type="text/plain")

    # 流式输出实现 (类似 tail -f)
    async def log_generator():
        # 先发送最后 N 行
        last_lines = read_last_lines(log_file, lines)
        for line in last_lines:
            yield line
            
        # 持续监听新内容
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            # 移动到文件末尾
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    # 检查节点是否还在运行，如果不在运行且没新日志了，就结束流
                    if node_id not in node_manager.active_workers:
                        # 再尝试读一次最后可能剩下的内容
                        line = f.readline()
                        if not line:
                            break
                    continue
                yield line

    return StreamingResponse(log_generator(), media_type="text/plain")

@router.get("/", response_model=List[NodeResponse])
async def list_nodes(current_admin: dict = Depends(get_current_admin)):
    """获取所有节点列表"""
    return await node_manager.get_all_nodes()

@router.post("/", response_model=NodeResponse)
async def create_node(node: NodeCreate, current_admin: dict = Depends(get_current_admin)):
    """创建新节点"""
    try:
        result = await node_manager.add_node(
            node.node_id, 
            node.queue_name, 
            node.max_concurrent
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{node_id}", response_model=bool)
async def update_node(node_id: str, node: NodeUpdate, current_admin: dict = Depends(get_current_admin)):
    """更新节点配置"""
    update_data = node.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    return await node_manager.update_node(node_id, update_data)

@router.post("/{node_id}/start")
async def start_node(node_id: str, current_admin: dict = Depends(get_current_admin)):
    """启动节点"""
    success = await node_manager.start_node(node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "success", "message": f"Node {node_id} started"}

@router.post("/{node_id}/stop")
async def stop_node(node_id: str, current_admin: dict = Depends(get_current_admin)):
    """停止节点"""
    success = await node_manager.stop_node(node_id)
    return {"status": "success", "message": f"Node {node_id} stopped"}

@router.delete("/{node_id}")
async def delete_node(node_id: str, current_admin: dict = Depends(get_current_admin)):
    """删除节点"""
    await node_manager.delete_node(node_id)
    return {"status": "success", "message": f"Node {node_id} deleted"}
