import os
import sys
from datetime import datetime

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.core.config import settings
from app.db.sqlite import sqlite_db
from app.core.logger import setup_logging
import logging

def init_configs():
    """
    将当前 settings (从 .env 加载) 中的配置项写入 SQLite 数据库
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("开始初始化系统配置到 SQLite 数据库...")
    
    # 获取 settings 中的所有配置项
    # 我们排除一些敏感或不需要在数据库中动态修改的内部字段
    exclude_keys = {'env_file', 'env_file_encoding', 'case_sensitive'}
    
    # 获取 Settings 类中定义的字段
    fields = settings.model_fields.keys()
    
    count = 0
    for key in fields:
        if key in exclude_keys:
            continue
            
        value = getattr(settings, key)
        
        # 检查数据库中是否已存在该配置
        existing = sqlite_db.get_config(key)
        
        # 预定义一些常见配置的友好描述
        descriptions = {
            "app_name": "应用名称，用于标识系统",
            "app_version": "系统当前版本号",
            "debug": "调试模式开关，开启后会输出详细日志",
            "host": "服务监听的主机地址",
            "port": "服务监听的端口号",
            "mongo_uri": "MongoDB 数据库连接 URI",
            "mongo_db": "MongoDB 数据库名称",
            "redis_url": "Redis 连接 URL，用于任务队列等",
            "redis_cache_url": "Redis 缓存连接 URL，用于存储抓取结果缓存",
            "rabbitmq_url": "RabbitMQ 消息队列连接 URL",
            "rabbitmq_queue": "RabbitMQ 默认任务队列名称",
            "rabbitmq_exchange": "RabbitMQ 交换机名称",
            "default_wait_for": "默认页面等待策略 (networkidle, load, domcontentloaded)",
            "default_timeout": "默认任务超时时间 (毫秒)",
            "user_agent": "默认浏览器 User-Agent",
            "stealth_mode": "是否默认开启反爬虫隐身模式",
            "cache_enabled": "是否全局启用结果缓存",
            "default_cache_ttl": "默认缓存过期时间 (秒)",
            "node_id": "当前工作节点的唯一标识符",
            "worker_concurrency": "单个 Worker 节点的并发任务数"
        }
        
        description = descriptions.get(key, f"系统配置项: {key}")

        if not existing:
            # 写入数据库
            sqlite_db.set_config(key, value, description)
            logger.info(f"已导入配置: {key} = {value}")
            count += 1
        else:
            # 即使存在，如果描述是默认的或者空的，我们也更新一下描述
            if not existing.get("description") or "从环境变量加载" in existing.get("description", ""):
                 sqlite_db.set_config(key, value, description)
                 logger.info(f"更新配置描述: {key}")
            else:
                 logger.debug(f"配置已存在且有自定义描述，跳过: {key}")
            
    logger.info(f"初始化完成，共导入 {count} 条配置。")

if __name__ == "__main__":
    init_configs()
