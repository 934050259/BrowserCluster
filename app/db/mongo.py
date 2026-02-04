"""
MongoDB 数据库连接管理模块

提供 MongoDB 的单例连接管理，包含数据库连接、集合访问等功能
"""
from pymongo import MongoClient
from app.core.config import settings


class MongoDB:
    """MongoDB 单例连接管理类"""

    _instance = None  # 单例实例
    _client = None  # MongoDB 客户端
    _db = None  # 数据库实例

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        """
        连接到 MongoDB

        Returns:
            Database: MongoDB 数据库实例
        """
        if self._client is None:
            self._client = MongoClient(settings.mongo_uri)
            self._db = self._client[settings.mongo_db]
        return self._db

    def close(self):
        """关闭 MongoDB 连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def db(self):
        """
        获取数据库实例，如果未连接则自动连接

        Returns:
            Database: MongoDB 数据库实例
        """
        if self._db is None:
            self.connect()
        return self._db

    @property
    def tasks(self):
        """
        获取任务集合

        Returns:
            Collection: tasks 集合
        """
        return self.db.tasks

    @property
    def task_stats(self):
        """
        获取任务统计集合

        Returns:
            Collection: task_stats 集合
        """
        return self.db.task_stats

    @property
    def configs(self):
        """
        获取配置集合

        Returns:
            Collection: configs 集合
        """
        return self.db.configs

    @property
    def parsing_rules(self):
        """
        获取解析规则集合

        Returns:
            Collection: parsing_rules 集合
        """
        return self.db.parsing_rules

    @property
    def nodes(self):
        """
        获取节点集合

        Returns:
            Collection: nodes 集合
        """
        return self.db.nodes

    @property
    def schedules(self):
        """
        获取定时任务集合

        Returns:
            Collection: schedules 集合
        """
        return self.db.schedules

    @property
    def users(self):
        """
        获取用户集合

        Returns:
            Collection: users 集合
        """
        return self.db.users


# 全局 MongoDB 实例
mongo = MongoDB()
