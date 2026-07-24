"""API v1 路由汇总"""

from fastapi import APIRouter

from app.api.v1.approval_router import router as approval_router
from app.api.v1.auth_router import router as auth_router
from app.api.v1.contract_router import router as contract_router
from app.api.v1.dashboard_router import router as dashboard_router
from app.api.v1.risk_router import router as risk_router
from app.api.v1.system_router import router as system_router
from app.api.v1.task_router import router as task_router
from app.api.v1.webhook_router import router as webhook_router

router = APIRouter(prefix="/api/v1")

# 注册子路由
router.include_router(auth_router, tags=["认证"])
router.include_router(task_router, tags=["任务管理"])
router.include_router(approval_router, tags=["审批单管理"])
router.include_router(contract_router, tags=["合同文档"])
router.include_router(risk_router, tags=["风险审查"])
router.include_router(dashboard_router, tags=["统计看板"])
router.include_router(system_router, tags=["系统管理"])
router.include_router(webhook_router, tags=["Webhook 回调"])