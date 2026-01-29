"""
Redis 连接管理模块

提供 Redis 的单例连接管理，分别管理缓存和队列两个 Redis 实例
"""
import redis
from app.core.config import settings


class RedisClient:
    """Redis 单例连接管理类"""

    _instance = None  # 单例实例
    _cache_client = None  # 缓存客户端
    _queue_client = None  # 队列客户端

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect_cache(self):
        """
        连接到缓存 Redis 实例

        Returns:
            Redis: Redis 客户端实例
        """
        if self._cache_client is None:
            self._cache_client = redis.from_url(settings.redis_cache_url, decode_responses=True)
        return self._cache_client

    def connect_queue(self):
        """
        连接到队列 Redis 实例

        Returns:
            Redis: Redis 客户端实例
        """
        if self._queue_client is None:
            self._queue_client = redis.from_url(settings.redis_url, decode_responses=True)
        return self._queue_client

    @property
    def cache(self):
        """
        获取缓存客户端，如果未连接则自动连接

        Returns:
            Redis: 缓存客户端
        """
        if self._cache_client is None:
            self.connect_cache()
        return self._cache_client

    @property
    def queue(self):
        """
        获取队列客户端，如果未连接则自动连接

        Returns:
            Redis: 队列客户端
        """
        if self._queue_client is None:
            self.connect_queue()
        return self._queue_client

    def close_cache(self):
        """关闭缓存连接"""
        if self._cache_client:
            self._cache_client.close()
            self._cache_client = None

    def close_queue(self):
        """关闭队列连接"""
        if self._queue_client:
            self._queue_client.close()
            self._queue_client = None

    def close_all(self):
        """关闭所有 Redis 连接"""
        self.close_cache()
        self.close_queue()


# 全局 Redis 客户端实例
redis_client = RedisClient()
