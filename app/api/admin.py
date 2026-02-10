"""
配置管理 API 路由模块

提供系统配置的增删改查功能
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional, List
import time
import sys
import os
import asyncio
import re
from datetime import datetime
from app.models.config import ConfigModel
from app.db.sqlite import sqlite_db
from app.core.config import settings
from app.services.node_manager import node_manager
from app.core.auth import get_current_admin

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/configs", tags=["Configs"])


@router.get("/logs/dates", response_model=List[str])
async def get_system_log_dates(current_admin: dict = Depends(get_current_admin)):
    """
    获取系统日志所有可用的历史日期列表
    """
    log_file = settings.log_file
    log_dir = os.path.dirname(log_file)
    if not log_dir:
        log_dir = "."
    
    if not os.path.exists(log_dir):
        return []
    
    base_name = os.path.basename(log_file)
    dates = set()
    
    # 匹配文件名格式: app.log.YYYY-MM-DD
    # 或者如果主日志文件本身就带日期
    date_pattern = re.compile(r".*?(\d{4}-\d{2}-\d{2})$")
    
    try:
        for filename in os.listdir(log_dir):
            # 检查是否是该日志文件的滚动版本
            if filename.startswith(base_name):
                match = date_pattern.search(filename)
                if match:
                    dates.add(match.group(1))
            # 或者文件名本身包含日期且与日志相关
            elif "app" in filename and "log" in filename:
                match = date_pattern.search(filename)
                if match:
                    dates.add(match.group(1))
                    
        # 加上今天的日期，如果主日志文件存在
        if os.path.exists(log_file):
            today = datetime.now().strftime("%Y-%m-%d")
            dates.add(today)
                
        # 排序，倒序排列（最新的在前）
        sorted_dates = sorted(list(dates), reverse=True)
        return sorted_dates
    except Exception as e:
        logger.error(f"Error listing log dates: {e}")
        return []


@router.get("/logs")
async def get_system_logs(
    lines: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    stream: bool = Query(False),
    date: Optional[str] = Query(None, description="筛选日期 (YYYY-MM-DD)"),
    download: bool = Query(False, description="是否下载日志文件"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取系统主日志
    
    Args:
        lines: 返回多少行日志
        offset: 从末尾跳过多少行 (用于滚动加载历史数据)
        stream: 是否实时流式输出 (仅在 offset 为 0 且未指定 date 时生效)
        date: 筛选日期 (YYYY-MM-DD)
        download: 是否作为文件下载
    """
    log_file = settings.log_file
    
    # 修复当天日期匹配逻辑
    target_file = log_file
    if date:
        today = datetime.now().strftime("%Y-%m-%d")
        # 如果是今天，直接使用主日志文件
        if date == today:
            target_file = log_file
        else:
            # 尝试匹配常见的滚动日志命名约定 app.log.YYYY-MM-DD
            date_log_file = f"{log_file}.{date}"
            if os.path.exists(date_log_file):
                target_file = date_log_file
            elif not log_file.endswith(date) and date not in log_file:
                if not download:
                    return StreamingResponse(iter([f"No logs found for date: {date}"]), media_type="text/plain")
                else:
                    raise HTTPException(status_code=404, detail=f"No logs found for date: {date}")

    if not os.path.exists(target_file):
        return StreamingResponse(iter(["Waiting for system logs..."]), media_type="text/plain")

    if download:
        filename = os.path.basename(target_file)
        if date and not date in filename:
            filename = f"system-{date}.log"
        
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
                # 获取总行数 (对于大文件，这可能有点慢，但在 50000 行限制内还好)
                all_lines = f.readlines()
                total = len(all_lines)
                
                # 计算读取范围 (从后往前)
                end = total - skip_count
                start = max(0, end - lines_count)
                
                if start >= end:
                    return []
                return all_lines[start:end]
        except Exception as e:
            return [f"Error reading log file: {str(e)}"]

    # 如果指定了 offset 或指定了日期且非流式，使用范围读取实现“滚动加载”
    if not stream or offset > 0 or (date and date != datetime.now().strftime("%Y-%m-%d")):
        content = "".join(read_logs_range(target_file, lines, offset))
        return StreamingResponse(iter([content]), media_type="text/plain")

    # 流式输出实现 (仅对主日志文件有效)
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
            
        # 持续监听新内容 (仅当是主日志文件且无日期筛选时)
        if not date or target_file == log_file:
            try:
                with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # 移动到文件末尾
                    f.seek(0, os.SEEK_END)
                    while True:
                        line = f.readline()
                        if not line:
                            await asyncio.sleep(0.5)
                            continue
                        yield line
            except Exception as e:
                yield f"\n[Log Stream Error: {str(e)}]"

    return StreamingResponse(log_generator(), media_type="text/plain")


@router.get("/schema")
async def get_config_schema(current_admin: dict = Depends(get_current_admin)):
    """
    获取配置 schema，包含所有可配置项及其默认值
    """
    # 获取 Settings 类的 JSON Schema
    schema = settings.model_json_schema()
    
    # 提取属性及其默认值
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    result = []
    for key, prop in properties.items():
        # 获取当前值（如果已加载）
        current_value = getattr(settings, key, None)
        
        result.append({
            "key": key,
            "title": prop.get("title", key),
            "type": prop.get("type", "string"),
            "default": prop.get("default"),
            "description": prop.get("description", ""),
            "required": key in required,
            "current_value": current_value
        })
    
    return result


@router.post("/restart")
async def restart_system(background_tasks: BackgroundTasks, current_admin: dict = Depends(get_current_admin)):
    """
    强制重启系统
    """
    # 在重启前停止所有正在运行的节点
    await node_manager.stop_all_nodes()
    
    def restart():
        # 给一点时间让响应返回
        time.sleep(1.0)
        logger.info("系统正在重启...")
        try:
            # 1. 如果是调试模式（uvicorn reload），通过 touch main.py 触发重启
            if settings.debug:
                main_py = os.path.join(os.getcwd(), "app", "main.py")
                if os.path.exists(main_py):
                    os.utime(main_py, None)
                    logger.info("已触发 uvicorn 热重载")
                    return

            # 2. 如果是非调试模式，或者 touch 无效，尝试直接重启进程
            # 获取当前运行的命令行参数
            args = sys.argv[:]
            if not args[0].endswith('.exe') and not args[0].endswith('python'):
                args.insert(0, sys.executable)
            
            logger.info(f"直接重启进程: {' '.join(args)}")
            if sys.platform == 'win32':
                # Windows 下使用 subprocess 启动新进程并退出旧进程
                import subprocess
                subprocess.Popen(args, close_fds=True)
                os._exit(0)
            else:
                # Unix/Linux 下使用 os.execv 替换当前进程
                os.execv(sys.executable, args)
        except Exception as e:
            logger.error(f"重启失败: {e}")
            os._exit(1)

    background_tasks.add_task(restart)
    return {"message": "System restart initiated"}


@router.get("/export")
async def export_configs_env(current_admin: dict = Depends(get_current_admin)):
    """
    导出配置为 .env 格式文件
    """
    # 1. 获取所有配置
    # 获取数据库中的配置
    db_configs = sqlite_db.get_all_configs()
    db_map = {c["key"]: c for c in db_configs}
    
    # 获取 Settings 类的 JSON Schema 以便按顺序导出并获取描述
    schema = settings.model_json_schema()
    properties = schema.get("properties", {})
    
    env_content = []
    env_content.append(f"# Browser Cluster Configuration - Exported at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    env_content.append("# Format compatible with .env files\n")
    
    # 2. 遍历 schema 中的键，优先导出
    for key in properties.keys():
        # 获取值：优先从数据库获取，如果没有则从 settings 获取（即默认值）
        value = None
        description = properties[key].get("description", "")
        
        if key in db_map:
            value = db_map[key]["value"]
            # 如果数据库中有描述，使用数据库的
            if db_map[key].get("description"):
                description = db_map[key]["description"]
        else:
            value = getattr(settings, key, None)
            
        if value is None:
            value = ""
            
        # 写入描述注释
        if description:
            env_content.append(f"# {description}")
        
        # 转换值为字符串，布尔值转为小写
        if isinstance(value, bool):
            val_str = str(value).lower()
        else:
            val_str = str(value)
            
        env_content.append(f"{key.upper()}={val_str}\n")
        
    # 3. 导出数据库中存在但不在 schema 中的键（自定义动态配置）
    custom_keys = [k for k in db_map.keys() if k not in properties]
    if custom_keys:
        env_content.append("# Custom/Dynamic Configurations")
        for key in custom_keys:
            value = db_map[key]["value"]
            description = db_map[key].get("description", "Custom configuration")
            env_content.append(f"# {description}")
            env_content.append(f"{key.upper()}={value}\n")
            
    content = "\n".join(env_content)
    
    return StreamingResponse(
        iter([content]), 
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=browser_cluster_{time.strftime('%Y%m%d_%H%M%S')}.env"}
    )


@router.get("/")
async def list_configs(current_admin: dict = Depends(get_current_admin)):
    """
    获取所有配置

    Returns:
        list: 配置列表
    """
    configs = sqlite_db.get_all_configs()
    return configs


@router.post("/")
async def create_config(config: ConfigModel, current_admin: dict = Depends(get_current_admin)):
    """
    创建新配置

    Args:
        config: 配置数据

    Returns:
        dict: 创建结果

    Raises:
        HTTPException: 配置键已存在时返回 400
    """
    # 检查配置键是否已存在
    existing = sqlite_db.get_config(config.key)
    if existing:
        raise HTTPException(status_code=400, detail="Config key already exists")

    # 插入新配置
    sqlite_db.set_config(config.key, config.value, config.description)

    # 立即从数据库重载配置到内存中的 settings 对象
    settings.load_from_db()

    return {"message": "Config created", "key": config.key}


@router.put("/{key}")
async def update_config(key: str, value: dict, current_admin: dict = Depends(get_current_admin)):
    """
    更新配置

    Args:
        key: 配置键
        value: 新值

    Returns:
        dict: 更新结果

    Raises:
        HTTPException: 配置不存在时返回 404
    """
    # 检查配置是否存在
    existing = sqlite_db.get_config(key)
    if not existing:
        raise HTTPException(status_code=404, detail="Config not found")

    # 更新配置
    sqlite_db.set_config(key, value.get("value"), existing.get("description"))

    # 立即从数据库重载配置到内存中的 settings 对象
    settings.load_from_db()

    return {"message": "Config updated"}


@router.delete("/{key}")
async def delete_config(key: str, current_admin: dict = Depends(get_current_admin)):
    """
    删除配置

    Args:
        key: 配置键

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 配置不存在时返回 404
    """
    success = sqlite_db.delete_config(key)

    if not success:
        raise HTTPException(status_code=404, detail="Config not found")

    # 立即从数据库重载配置到内存中的 settings 对象
    settings.load_from_db()

    return {"message": "Config deleted"}
