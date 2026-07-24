"""APScheduler 调度器集成"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

# 全局调度器实例，使用 Asia/Shanghai 时区
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


# ==================== 生命周期 ====================

def init_scheduler() -> None:
    """初始化并启动调度器"""
    scheduler.start()
    logger.info("APScheduler 调度器已启动")


def shutdown_scheduler() -> None:
    """关闭调度器，等待当前任务完成"""
    scheduler.shutdown(wait=False)
    logger.info("APScheduler 调度器已关闭")


# ==================== 任务管理 ====================

def add_interval_job(func, job_id: str, seconds: int, **kwargs) -> None:
    """添加间隔执行任务（如每 5 分钟拉取一次审批单）"""
    scheduler.add_job(
        func,
        trigger=IntervalTrigger(seconds=seconds),
        id=job_id,
        replace_existing=True,       # 同名任务自动替换
        **kwargs,
    )
    logger.info(f"调度任务已添加 | job_id={job_id} | interval={seconds}s")


def add_cron_job(func, job_id: str, cron_expr: str, **kwargs) -> None:
    """添加 Cron 定时任务（如每天凌晨 2 点清理）"""
    parts = cron_expr.strip().split()
    if len(parts) == 5:
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )
    else:
        raise ValueError(f"无效的 Cron 表达式: {cron_expr}")

    scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        **kwargs,
    )
    logger.info(f"调度任务已添加 | job_id={job_id} | cron={cron_expr}")


def remove_job(job_id: str) -> None:
    """移除调度任务"""
    scheduler.remove_job(job_id)
    logger.info(f"调度任务已移除 | job_id={job_id}")


# ==================== 状态查询 ====================

def get_jobs() -> list[dict]:
    """获取所有调度任务状态"""
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]
