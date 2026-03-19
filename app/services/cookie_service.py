import httpx
import asyncio
import random
import logging
import json
from typing import List, Optional, Dict, Union
from datetime import datetime, timedelta
from app.db.redis import redis_client
from app.models.cookie import (
    Cookie, CookieCreate, CookieUpdate, CookieFilter, 
    CookieConfig, CookieStats, CookieListResponse
)
from app.db.sqlite import sqlite_db
from app.core.config import settings

logger = logging.getLogger(__name__)

class CookiePoolService:
    """Cookie 池服务类"""
    
    def __init__(self):
        """初始化 Cookie 服务"""
        # 强制从数据库重新加载配置
        settings.load_from_db()
        self._config_callbacks = []
        
        # Lua 脚本：原子性检查并增加频率计数
        # KEYS[1]: rate_key
        # ARGV[1]: expire_time (秒)
        # ARGV[2]: limit (最大次数)
        # 返回: 1 成功获取, 0 超过限制
        self._acquire_script = self.redis.register_script("""
            local current = tonumber(redis.call('get', KEYS[1]) or "0")
            if current >= tonumber(ARGV[2]) then
                return 0
            end
            local new_val = redis.call('incr', KEYS[1])
            if new_val == 1 then
                redis.call('expire', KEYS[1], ARGV[1])
            end
            return 1
        """)

    def register_config_callback(self, callback):
        """注册配置变更回调"""
        if callback not in self._config_callbacks:
            self._config_callbacks.append(callback)

    @property
    def base_key(self) -> str:
        return settings.cookie_redis_key_prefix

    @property
    def details_key(self) -> str:
        return f"{self.base_key}:details"

    def get_pool_key(self, domain: str) -> str:
        return f"{self.base_key}:pool:{domain}"

    @property
    def redis(self):
        return redis_client.cookie

    def _get_cookie_id(self, domain: str, username: str) -> str:
        return f"{domain}:{username}"

    async def add_cookie(self, cookie_data: CookieCreate) -> Cookie:
        """添加 Cookie"""
        cookie_id = self._get_cookie_id(cookie_data.domain, cookie_data.username)
        
        # 如果未指定 rate_limit，使用默认配置
        rate_limit = cookie_data.rate_limit or settings.cookie_default_rate_limit
        
        cookie = Cookie(
            id=cookie_id,
            domain=cookie_data.domain,
            username=cookie_data.username,
            password=cookie_data.password,
            value=cookie_data.value,
            group=cookie_data.group,
            rate_limit=rate_limit
        )
        
        # 保存详情
        self.redis.hset(self.details_key, cookie_id, cookie.to_redis_val())
        
        # 添加到 domain 池
        if cookie.status == "active":
            await self._add_to_pool(cookie_id, cookie.domain)
            
        logger.info(f"Added cookie: {cookie_id}")
        return cookie

    async def get_cookie_by_id(self, cookie_id: str) -> Optional[Cookie]:
        """获取 Cookie 详情"""
        val = self.redis.hget(self.details_key, cookie_id)
        if val:
            return Cookie.from_redis_val(val)
        return None

    async def update_cookie(self, cookie_id: str, update_data: CookieUpdate) -> Optional[Cookie]:
        """更新 Cookie"""
        cookie = await self.get_cookie_by_id(cookie_id)
        if not cookie:
            return None
            
        old_status = cookie.status
        old_domain = cookie.domain # domain 不允许修改，但为了逻辑完整
        
        # 更新字段
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(cookie, key, value)
            
        new_status = cookie.status
        
        # 处理状态变更
        if old_status == "active" and new_status != "active":
            await self._remove_from_pool(cookie_id, old_domain)
        elif old_status != "active" and new_status == "active":
            await self._add_to_pool(cookie_id, old_domain)
            
        # 保存更新
        self.redis.hset(self.details_key, cookie_id, cookie.to_redis_val())
        return cookie

    async def delete_cookie(self, cookie_id: str) -> bool:
        """删除 Cookie"""
        cookie = await self.get_cookie_by_id(cookie_id)
        if cookie:
            await self._remove_from_pool(cookie_id, cookie.domain)
        return self.redis.hdel(self.details_key, cookie_id) > 0

    async def bulk_delete_cookies(self, cookie_ids: List[str]) -> int:
        """批量删除 Cookie"""
        count = 0
        for cookie_id in cookie_ids:
            if await self.delete_cookie(cookie_id):
                count += 1
        return count

    async def list_cookies(self, filter_data: Optional[CookieFilter] = None, skip: int = 0, limit: int = 100) -> Dict:
        """列出 Cookie"""
        all_details = self.redis.hgetall(self.details_key)
        cookies = []
        for val in all_details.values():
            try:
                cookie = Cookie.from_redis_val(val)
            except Exception as e:
                logger.error(f"Error parsing cookie: {e}")
                continue
                
            if filter_data:
                if filter_data.domain and cookie.domain != filter_data.domain:
                    continue
                if filter_data.group and cookie.group != filter_data.group:
                    continue
                if filter_data.status and cookie.status != filter_data.status:
                    continue
            
            cookies.append(cookie)
        
        # 排序：优先显示 active，然后按 ID
        cookies.sort(key=lambda x: (x.status != "active", x.id))
        
        total = len(cookies)
        paged_cookies = cookies[skip : skip + limit]
        
        return {
            "total": total,
            "items": paged_cookies
        }

    async def get_best_cookie(self, domain: str, group: str = "default") -> Optional[Cookie]:
        """
        获取最佳可用 Cookie (考虑频率限制)
        """
        pool_key = self.get_pool_key(domain)
        
        # 获取池中所有 Cookie ID
        cookie_ids = self.redis.smembers(pool_key)
        if not cookie_ids:
            return None
            
        # 转换为列表并打乱，实现简单的负载均衡
        candidates = list(cookie_ids)
        random.shuffle(candidates)
        
        for cookie_id in candidates:
            cookie = await self.get_cookie_by_id(cookie_id)
            if not cookie or cookie.group != group or cookie.status != "active":
                continue
                
            # 尝试原子性获取 Cookie (检查并增加计数)
            if await self._try_acquire_cookie(cookie):
                # 更新持久化统计信息 (非严格并发要求，仅用于 UI 展示)
                await self._update_usage_stats(cookie)
                return cookie
                
        return None

    async def _try_acquire_cookie(self, cookie: Cookie) -> bool:
        """原子性尝试获取 Cookie 额度"""
        if cookie.rate_limit <= 0:
            return True
            
        # 使用 Redis 计数器，Key: cookie:rate:{id}:{minute}
        current_minute = int(datetime.now().timestamp() // 60)
        rate_key = f"{self.base_key}:rate:{cookie.id}:{current_minute}"
        
        # 调用 Lua 脚本进行原子操作
        # KEYS[1]: rate_key, ARGV[1]: expire_time, ARGV[2]: limit
        success = self._acquire_script(keys=[rate_key], args=[65, cookie.rate_limit])
        
        if not success:
            logger.warning(f"Cookie {cookie.id} rate limit exceeded for minute {current_minute}")
            return False
            
        return True

    async def _update_usage_stats(self, cookie: Cookie):
        """更新持久化的使用统计 (UI 展示用)"""
        try:
            # 这里仅更新 Hash 中的统计信息，不影响频率限制逻辑
            cookie.total_count += 1
            cookie.last_used_at = datetime.now()
            self.redis.hset(self.details_key, cookie.id, cookie.to_redis_val())
        except Exception as e:
            logger.error(f"Failed to update cookie usage stats: {e}")

    async def _add_to_pool(self, cookie_id: str, domain: str):
        """添加到可用池"""
        pool_key = self.get_pool_key(domain)
        self.redis.sadd(pool_key, cookie_id)

    async def _remove_from_pool(self, cookie_id: str, domain: str):
        """从可用池移除"""
        pool_key = self.get_pool_key(domain)
        self.redis.srem(pool_key, cookie_id)

    async def check_cookie(self, cookie: Cookie) -> bool:
        """检测 Cookie 有效性"""
        if not settings.cookie_enable_check:
            return True
            
        # 简单实现：请求 domain 根路径
        # 注意：实际场景可能需要更复杂的逻辑，比如检查特定元素
        url = f"https://{cookie.domain}"
        
        try:
            # 转换 cookie 格式为 httpx 可用的
            # 假设 cookie.value 是 dict {name: value} 或 list of dicts
            cookies_to_use = {}
            if isinstance(cookie.value, dict):
                cookies_to_use = cookie.value
            elif isinstance(cookie.value, list):
                for c in cookie.value:
                    if isinstance(c, dict) and 'name' in c and 'value' in c:
                        cookies_to_use[c['name']] = c['value']
            
            async with httpx.AsyncClient(
                timeout=settings.cookie_check_timeout,
                verify=False,
                follow_redirects=True,
                headers={
                    "User-Agent": settings.user_agent
                },
                cookies=cookies_to_use
            ) as client:
                response = await client.get(url)
                
                # 简单的状态码检查，200-399 视为有效
                # 实际上很多网站未登录也是 200，这里只是最基本的连通性检查
                # 更高级的检查需要针对 domain 定制逻辑
                if 200 <= response.status_code < 400:
                    cookie.fail_count = 0
                    if cookie.status != "active":
                        cookie.status = "active"
                        await self._add_to_pool(cookie.id, cookie.domain)
                else:
                    logger.warning(f"Cookie check failed for {cookie.id}: status {response.status_code}")
                    cookie.fail_count += 1
        except Exception as e:
            logger.error(f"Cookie check error for {cookie.id}: {e}")
            cookie.fail_count += 1
            
        # 检查是否失效
        if cookie.fail_count >= settings.cookie_fail_threshold:
            if cookie.status == "active":
                cookie.status = "inactive"
                await self._remove_from_pool(cookie.id, cookie.domain)
                logger.warning(f"Cookie {cookie.id} marked as inactive due to failures")
        
        cookie.last_check_at = datetime.now()
        self.redis.hset(self.details_key, cookie.id, cookie.to_redis_val())
        
        return cookie.status == "active"

    async def check_all_cookies(self):
        """检测所有 Cookie"""
        result = await self.list_cookies(limit=10000)
        cookies = result["items"]
        
        logger.info(f"Starting scheduled cookie check for {len(cookies)} cookies")
        
        if not cookies:
            return

        # 并发检测
        tasks = [self.check_cookie(c) for c in cookies]
        await asyncio.gather(*tasks)
        logger.info(f"Finished checking {len(tasks)} cookies")

    async def get_stats(self) -> CookieStats:
        """获取统计信息"""
        result = await self.list_cookies(limit=10000)
        cookies = result["items"]
        
        total = len(cookies)
        active = len([c for c in cookies if c.status == "active"])
        invalid = len([c for c in cookies if c.status != "active"])
        
        domains = list(set(c.domain for c in cookies))
        groups = list(set(c.group for c in cookies))
        
        return CookieStats(
            total=total,
            active=active,
            invalid=invalid,
            domains=domains,
            groups=groups
        )
        
    async def get_config(self) -> CookieConfig:
        """获取配置"""
        return CookieConfig(
            cookie_enable_check=settings.cookie_enable_check,
            cookie_check_interval=settings.cookie_check_interval,
            cookie_check_timeout=settings.cookie_check_timeout,
            cookie_fail_threshold=settings.cookie_fail_threshold,
            cookie_default_rate_limit=settings.cookie_default_rate_limit
        )

    async def update_config(self, config: CookieConfig) -> bool:
        """更新配置"""
        data = config.model_dump()
        for key, value in data.items():
            sqlite_db.set_config(key, value)
        
        settings.load_from_db()
        
        for cb in self._config_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb()
                else:
                    cb()
            except Exception as e:
                logger.error(f"Error in cookie config callback: {e}")
                
        return True

    async def bulk_import(self, cookies_data: List[CookieCreate]) -> int:
        """批量导入"""
        count = 0
        for data in cookies_data:
            await self.add_cookie(data)
            count += 1
        return count

    async def bulk_export(self) -> List[CookieCreate]:
        """批量导出"""
        result = await self.list_cookies(limit=10000)
        return [
            CookieCreate(
                domain=c.domain,
                username=c.username,
                password=c.password,
                value=c.value,
                group=c.group,
                rate_limit=c.rate_limit
            ) for c in result["items"]
        ]

# 单例
cookie_service = CookiePoolService()
