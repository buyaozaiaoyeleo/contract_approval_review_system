"""Redis 分布式锁"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger

from app.infrastructure.redis_client import redis_client


class DistributedLock:
    """基于 Redis Lua 脚本的分布式锁

    使用 SET NX PX 实现加锁，Lua 脚本实现原子释放。
    避免因进程崩溃导致的死锁问题。
    """

    def __init__(self):
        self._lua_acquire = None
        self._lua_release = None

    def _load_scripts(self):
        """加载 Lua 脚本到 Redis 服务端"""
        # 加锁脚本：仅当 key 不存在时 SET，同时设置过期时间
        self._lua_acquire = redis_client.client.register_script("""
            if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
                return 1
            else
                return 0
            end
        """)
        # 释放脚本：仅当锁的持有者匹配时才删除（防止误删他人锁）
        self._lua_release = redis_client.client.register_script("""
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            else
                return 0
            end
        """)

    # ==================== 锁操作 ====================

    async def acquire(
        self,
        lock_key: str,
        expire_ms: int = 30000,
        retry_times: int = 3,
        retry_interval_ms: int = 200,
    ) -> str | None:
        """获取分布式锁，返回锁标识（lock_id），失败返回 None"""
        lock_id = str(uuid.uuid4())
        full_key = f"lock:{lock_key}"

        for attempt in range(retry_times + 1):
            # 使用 Lua 脚本原子执行 SET NX PX
            result = await self._lua_acquire(keys=[full_key], args=[lock_id, expire_ms])
            if result == 1:
                logger.debug(f"分布式锁获取成功 | key={lock_key} | lock_id={lock_id}")
                return lock_id
            if attempt < retry_times:
                await asyncio.sleep(retry_interval_ms / 1000)

        logger.warning(f"分布式锁获取失败 | key={lock_key} | retries={retry_times}")
        return None

    async def release(self, lock_key: str, lock_id: str) -> bool:
        """释放分布式锁（仅持有者可释放）"""
        full_key = f"lock:{lock_key}"
        result = await self._lua_release(keys=[full_key], args=[lock_id])
        released = result == 1
        if released:
            logger.debug(f"分布式锁释放成功 | key={lock_key} | lock_id={lock_id}")
        else:
            logger.warning(f"分布式锁释放失败(可能已过期) | key={lock_key} | lock_id={lock_id}")
        return released

    async def extend(self, lock_key: str, lock_id: str, expire_ms: int) -> bool:
        """续期锁的过期时间"""
        full_key = f"lock:{lock_key}"
        current = await redis_client.get(full_key)
        if current == lock_id:
            await redis_client.expire(full_key, expire_ms // 1000)
            return True
        return False

    # ==================== 上下文管理器 ====================

    @asynccontextmanager
    async def lock(
        self,
        lock_key: str,
        expire_ms: int = 30000,
        retry_times: int = 3,
    ) -> AsyncGenerator[str | None, None]:
        """异步上下文管理器，自动获取和释放锁"""
        lock_id = await self.acquire(lock_key, expire_ms, retry_times)
        try:
            yield lock_id
        finally:
            if lock_id:
                await self.release(lock_key, lock_id)


distributed_lock = DistributedLock()
