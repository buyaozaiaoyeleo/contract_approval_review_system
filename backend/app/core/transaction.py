"""事务管理"""

from collections.abc import Callable
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession


def transactional(func: Callable):
    """事务装饰器：自动从函数参数中查找 AsyncSession 并 commit/rollback"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 优先从 kwargs 中查找 db 参数
        db: AsyncSession | None = kwargs.get("db")
        if db is None:
            # 其次从位置参数中查找 AsyncSession 实例
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db = arg
                    break

        # 没有找到 db 会话，直接执行原函数
        if db is None:
            return await func(*args, **kwargs)

        try:
            result = await func(*args, **kwargs)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    return wrapper


class TransactionManager:
    """事务上下文管理器，用于 with 语句中手动控制事务边界"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.db.rollback()
            return False
        await self.db.commit()
        return True
