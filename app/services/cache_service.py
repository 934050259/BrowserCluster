"""
Redis 缓存服务模块

提供任务结果缓存功能
"""
import hashlib
import json
import logging
from typing import Optional, Any
from app.db.redis import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""

    def generate_cache_key(self, url: str, params: dict) -> str:
        """
        生成缓存键

        Args:
            url: 目标 URL
            params: 抓取参数

        Returns:
            str: MD5 哈希后的缓存键
        """
        # 将参数转换为排序后的 JSON 字符串
        params_str = json.dumps(params, sort_keys=True)
        # 组合 URL 和参数
        cache_input = f"{url}:{params_str}"
        # 生成 MD5 哈希
        return hashlib.md5(cache_input.encode()).hexdigest()

    async def get(self, url: str, params: dict) -> Optional[dict]:
        """
        从缓存获取数据

        Args:
            url: 目标 URL
            params: 抓取参数

        Returns:
            Optional[dict]: 缓存数据，如果不存在或缓存未启用则返回 None
        """
        # 检查缓存是否启用
        if not settings.cache_enabled:
            return None

        # 生成缓存键
        cache_key = self.generate_cache_key(url, params)

        try:
            # 从 Redis 获取缓存
            cached_data = redis_client.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")

        return None

    async def set(
        self,
        url: str,
        params: dict,
        data: dict,
        ttl: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> bool:
        """
        设置缓存

        Args:
            url: 目标 URL
            params: 抓取参数
            data: 要缓存的数据
            ttl: 过期时间（秒），如果不指定则使用默认值
            task_id: 关联的任务 ID（可选）

        Returns:
            bool: 是否成功设置缓存
        """
        # 检查缓存是否启用
        if not settings.cache_enabled:
            return False

        # 生成缓存键
        cache_key = self.generate_cache_key(url, params)
        # 使用指定的 TTL 或默认 TTL
        ttl = ttl or settings.default_cache_ttl

        try:
            # 如果提供了 task_id，将其添加到缓存数据中
            if task_id:
                data["task_id"] = task_id
                
            # 设置缓存，带过期时间
            redis_client.cache.setex(
                cache_key,
                ttl,
                json.dumps(data)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, url: str, params: dict) -> bool:
        """
        删除缓存

        Args:
            url: 目标 URL
            params: 抓取参数

        Returns:
            bool: 是否成功删除缓存
        """
        cache_key = self.generate_cache_key(url, params)

        try:
            redis_client.cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_by_key(self, cache_key: str) -> bool:
        """
        根据缓存键删除缓存

        Args:
            cache_key: 缓存键

        Returns:
            bool: 是否成功删除缓存
        """
        try:
            redis_client.cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete by key error: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 是否成功清空缓存
        """
        try:
            redis_client.cache.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# 全局缓存服务实例
cache_service = CacheService()
