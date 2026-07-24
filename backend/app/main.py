"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.common.snowflake import init_snowflake
from app.core.config import settings
from app.core.database import close_db
from app.core.exception_handlers import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging
from app.core.scheduler import init_scheduler, shutdown_scheduler
from app.infrastructure.distributed_lock import distributed_lock
from app.infrastructure.minio_client import minio_client
from app.infrastructure.redis_client import redis_client
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动阶段
    setup_logging()
    logger.info(f"应用启动中... | {settings.APP_NAME} v{settings.APP_VERSION} | env={settings.APP_ENV}")

    # 初始化雪花 ID 生成器
    init_snowflake(
        worker_id=settings.SNOWFLAKE_WORKER_ID,
        datacenter_id=settings.SNOWFLAKE_DATACENTER_ID,
    )
    logger.info(
        f"雪花 ID 生成器初始化完成 | worker_id={settings.SNOWFLAKE_WORKER_ID} "
        f"datacenter_id={settings.SNOWFLAKE_DATACENTER_ID}"
    )

    logger.info(f"应用启动完成 | 监听 {settings.SERVER_HOST}:{settings.SERVER_PORT}")

    # 连接 Redis
    try:
        await redis_client.connect()
        distributed_lock._load_scripts()
        logger.info("Redis 客户端 + 分布式锁初始化完成")
    except Exception as e:
        logger.warning(f"Redis 连接失败(非致命): {e}")

    # 连接 MinIO
    try:
        minio_client.connect()
        minio_client.ensure_bucket()
        logger.info("MinIO 客户端初始化完成")
    except Exception as e:
        logger.warning(f"MinIO 连接失败(非致命): {e}")

    # 启动调度器
    try:
        init_scheduler()
    except Exception as e:
        logger.warning(f"调度器启动失败(非致命): {e}")

    yield

    # 关闭阶段
    logger.info("应用正在关闭...")
    shutdown_scheduler()
    await redis_client.close()
    minio_client.close()
    await close_db()
    logger.info("所有资源已释放")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="企业级合同审批审查系统",
        lifespan=lifespan,
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
    )

    # 注册中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    # 注册全局异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 注册路由
    app.include_router(v1_router)

    return app


app = create_app()
