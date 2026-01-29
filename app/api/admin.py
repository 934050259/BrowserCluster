"""
配置管理 API 路由模块

提供系统配置的增删改查功能
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
import time
import sys
import os
import asyncio
from app.models.config import ConfigModel
from app.db.sqlite import sqlite_db
from app.core.config import settings
from app.services.node_manager import node_manager
from app.core.auth import get_current_admin

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/configs", tags=["Configs"])


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
