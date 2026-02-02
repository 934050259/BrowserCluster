#!/usr/bin/env python3
"""
数据库初始化脚本

连接到数据库并创建必要的索引
"""
import os
import sys
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongo import mongo
from app.db.redis import redis_client
from app.core.config import settings

if __name__ == "__main__":
    print("Initializing database...")

    # 连接到 MongoDB 和 Redis
    mongo.connect()
    redis_client.connect_cache()
    redis_client.connect_queue()

    print(f"Connected to MongoDB: {settings.mongo_uri}")
    print(f"Connected to Redis: {settings.redis_url}")

    # 创建 tasks 集合索引
    mongo.tasks.create_index("task_id", unique=True)  # 任务 ID 唯一索引
    mongo.tasks.create_index("status")  # 任务状态索引
    mongo.tasks.create_index("created_at")  # 创建时间索引
    mongo.tasks.create_index("cache_key")  # 缓存键索引

    # 创建 task_stats 集合索引
    mongo.task_stats.create_index("date", unique=True)  # 日期唯一索引

    # 创建 configs 集合索引
    mongo.configs.create_index("key", unique=True)  # 配置键唯一索引

    # 创建 nodes 集合索引
    mongo.nodes.create_index("node_id", unique=True)  # 节点 ID 唯一索引

    # 创建 parsing_rules 集合索引
    mongo.parsing_rules.drop_indexes() # 先清除旧索引
    mongo.parsing_rules.create_index("domain", unique=True)  # 域名唯一索引，一个域名只能有一条规则

    print("Database indexes created successfully!")

    # 关闭数据库连接
    mongo.close()
    redis_client.close_all()

    print("Database initialization completed!")
