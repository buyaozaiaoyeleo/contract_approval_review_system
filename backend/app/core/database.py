"""数据库引擎与会话管理"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 异步数据库引擎，连接池配置从 settings 读取
engine = create_async_engine(
    settings.database_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,          # 每次使用前检查连接有效性
    pool_recycle=3600,           # 每小时回收连接，防止 MySQL 8小时超时
)

# 异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,      # 提交后不过期对象，避免 lazy load 报错
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有模型继承此类"""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话，用于 FastAPI 依赖注入"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()      # 请求正常结束时提交
        except Exception:
            await session.rollback()    # 发生异常时回滚
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        async with engine.connect() as conn:
            await conn.execute(await conn.run_sync(lambda _: None))
        return True
    except Exception:
        return False


async def close_db() -> None:
    """关闭数据库连接池，释放所有连接"""
    await engine.dispose()
