"""日志系统配置 - 基于 loguru"""

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


class LoguruHandler(logging.Handler):
    """将标准库 logging 桥接到 loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """初始化日志系统"""

    # 移除 loguru 默认 handler
    logger.remove()

    # ==================== 日志格式 ====================

    if settings.LOG_FORMAT == "json":
        # 结构化 JSON 格式（生产环境推荐）
        log_format = (
            '{{'
            '"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"trace_id": "{extra[trace_id]}", '
            '"module": "{name}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"'
            '}}'
        )
    else:
        # 人类可读格式（开发环境）
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<yellow>{extra[trace_id]}</yellow> | "
            "<level>{message}</level>"
        )

    # ==================== 控制台输出 ====================

    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=not settings.is_production,       # 生产环境关闭颜色
        enqueue=True,                               # 多线程安全
    )

    # ==================== 文件输出 ====================

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 全量日志文件（按大小轮转）
    logger.add(
        log_dir / "app.{time:YYYY-MM-DD}.log",
        format=log_format,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
    )

    # 错误日志单独存储，便于快速排查
    logger.add(
        log_dir / "error.{time:YYYY-MM-DD}.log",
        format=log_format,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
    )

    # ==================== 桥接标准库 logging ====================

    # 将标准库 logging 桥接到 loguru，统一日志输出
    logging.basicConfig(handlers=[LoguruHandler()], level=0, force=True)

    # 配置 trace_id 默认值，避免 KeyError
    logger.configure(extra={"trace_id": ""})

    logger.info(f"日志系统初始化完成 | 环境: {settings.APP_ENV} | 级别: {settings.LOG_LEVEL}")


def get_logger(name: str = __name__):
    """获取 logger 实例"""
    return logger.bind(name=name)
