from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional
import os
import asyncio
import re
from datetime import datetime
from app.models.node import NodeCreate, NodeResponse, NodeUpdate
from app.services.node_manager import node_manager
from app.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes"])

@router.get("/{node_id}/logs/dates", response_model=List[str])
async def get_node_log_dates(node_id: str, current_admin: dict = Depends(get_current_admin)):
    """
    获取指定节点日志所有可用的历史日期列表
    """
    log_file = f"logs/node-{node_id}.log"
    log_dir = os.path.dirname(log_file)
    if not log_dir:
        log_dir = "logs"
    
    if not os.path.exists(log_dir):
        return []
    
    base_name = os.path.basename(log_file)
    dates = set()
    
    # 匹配文件名格式: node-{node_id}.log.YYYY-MM-DD
    date_pattern = re.compile(r".*?(\d{4}-\d{2}-\d{2})$")
    
    try:
        for filename in os.listdir(log_dir):
            if filename.startswith(base_name):
                match = date_pattern.search(filename)
                if match:
                    dates.add(match.group(1))
                    
        # 加上今天的日期，如果主日志文件存在
        if os.path.exists(log_file):
            today = datetime.now().strftime("%Y-%m-%d")
            dates.add(today)
                
        # 排序，倒序排列
        sorted_dates = sorted(list(dates), reverse=True)
        return sorted_dates
    except Exception as e:
        return []


@router.get("/{node_id}/logs")
async def get_node_logs(
    node_id: str, 
    lines: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    stream: bool = Query(False),
    date: Optional[str] = Query(None, description="筛选日期 (YYYY-MM-DD)"),
    download: bool = Query(False, description="是否下载日志文件"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取节点运行日志
    
    Args:
        node_id: 节点 ID
        lines: 返回多少行日志
        offset: 从末尾跳过多少行
        stream: 是否实时流式输出
        date: 筛选日期 (YYYY-MM-DD)
        download: 是否作为文件下载
    """
    log_file = f"logs/node-{node_id}.log"
    
    # 修复当天日期匹配逻辑
    target_file = log_file
    if date:
        today = datetime.now().strftime("%Y-%m-%d")
        if date == today:
            target_file = log_file
        else:
            date_log_file = f"{log_file}.{date}"
            if os.path.exists(date_log_file):
                target_file = date_log_file
            elif not log_file.endswith(date) and date not in log_file:
                if not download:
                    return StreamingResponse(iter([f"No logs found for date: {date}"]), media_type="text/plain")
                else:
                    raise HTTPException(status_code=404, detail=f"No logs found for date: {date}")

    if not os.path.exists(target_file):
        # 如果是正在运行的节点但还没日志文件，可能还没产生日志
        if node_id in node_manager.active_workers:
            return StreamingResponse(iter(["Waiting for logs..."]), media_type="text/plain")
        raise HTTPException(status_code=404, detail="Log file not found for this node")

    if download:
        filename = os.path.basename(target_file)
        if date and not date in filename:
            filename = f"node-{node_id}-{date}.log"
        
        def iterfile():
            with open(target_file, mode="rb") as file_like:
                yield from file_like

        return StreamingResponse(
            iterfile(),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    def read_logs_range(file_path, lines_count, skip_count):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                total = len(all_lines)
                end = total - skip_count
                start = max(0, end - lines_count)
                if start >= end:
                    return []
                return all_lines[start:end]
        except:
            return []

    # 如果指定了 offset 或非今日日期的历史查询，使用范围读取
    if not stream or offset > 0 or (date and date != datetime.now().strftime("%Y-%m-%d")):
        content = "".join(read_logs_range(target_file, lines, offset))
        return StreamingResponse(iter([content]), media_type="text/plain")

    # 流式输出实现
    async def log_generator():
        # 先发送最后 N 行
        def read_last_lines(file_path, n):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    return all_lines[-n:]
            except:
                return []
                
        last_lines = read_last_lines(target_file, lines)
        for line in last_lines:
            yield line
            
        # 持续监听新内容
        if not date or target_file == log_file:
            with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
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
