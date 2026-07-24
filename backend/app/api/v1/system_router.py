"""系统管理 API 路由

提供系统配置管理、操作日志查询等接口。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.system_config import SystemConfig
from app.models.system_log import SystemLog

router = APIRouter(prefix="/system")


# ==================== 请求/响应模型 ====================

class ConfigResponse(BaseModel):
    """系统配置响应"""
    key: str
    value: str
    description: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    value: str = Field(..., min_length=1, description="配置值")


class LogResponse(BaseModel):
    """操作日志响应"""
    id: str
    level: str
    module: str
    message: str
    created_at: str | None

    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    """日志列表响应"""
    total: int
    items: list[LogResponse]


# ==================== 配置管理路由 ====================

@router.get(
    "/configs",
    response_model=list[ConfigResponse],
    summary="获取所有配置",
    description="获取系统所有配置项列表。",
)
async def get_configs(db: AsyncSession = Depends(get_db)):
    """获取所有系统配置"""

    result = await db.execute(
        select(SystemConfig).order_by(SystemConfig.config_key)
    )
    configs = list(result.scalars().all())

    return [
        ConfigResponse(
            key=c.config_key,
            value=c.config_value,
            description=c.description,
            updated_at=str(c.updated_at) if c.updated_at else None,
        )
        for c in configs
    ]


@router.put(
    "/configs/{config_key}",
    response_model=ConfigResponse,
    summary="更新配置",
    description="根据配置键更新系统配置值，如果不存在则创建。",
)
async def update_config(
    config_key: str,
    body: UpdateConfigRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """更新或创建系统配置"""

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()

    if config:
        config.config_value = body.value
    else:
        config = SystemConfig(
            config_key=config_key,
            config_value=body.value,
            description="动态创建的配置项",
        )
        db.add(config)

    await db.flush()
    await db.refresh(config)

    return ConfigResponse(
        key=config.config_key,
        value=config.config_value,
        description=config.description,
        updated_at=str(config.updated_at) if config.updated_at else None,
    )


# ==================== 操作日志路由 ====================

@router.get(
    "/logs",
    response_model=LogListResponse,
    summary="查询操作日志",
    description="分页查询系统操作日志，支持按级别和模块筛选。",
)
async def get_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    level: str | None = Query(None, description="按级别筛选: INFO/WARNING/ERROR/DEBUG"),
    module: str | None = Query(None, description="按模块筛选: risk/workflow/contract/approval/system"),
    db: AsyncSession = Depends(get_db),
):
    """分页查询操作日志"""

    # 构建查询条件
    conditions = []
    if level:
        conditions.append(SystemLog.level == level.upper())
    if module:
        conditions.append(SystemLog.module == module)

    # 总数
    count_query = select(func.count(SystemLog.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 列表
    list_query = select(SystemLog).order_by(SystemLog.created_at.desc())
    if conditions:
        list_query = list_query.where(*conditions)
    list_query = list_query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(list_query)
    logs = list(result.scalars().all())

    return LogListResponse(
        total=total,
        items=[
            LogResponse(
                id=str(log.id),
                level=log.level,
                module=log.module,
                message=log.message,
                created_at=str(log.created_at) if log.created_at else None,
            )
            for log in logs
        ],
    )
