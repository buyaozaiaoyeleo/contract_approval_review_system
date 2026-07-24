"""Webhook 回调 API 路由

提供 OA 系统回调接口，用于接收审批状态变更通知。
"""

import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.approval.approval_service import ApprovalService

router = APIRouter(prefix="/webhook")


# ==================== 请求模型 ====================

class ApprovalStatusWebhook(BaseModel):
    """审批状态变更 Webhook 请求体"""
    event: str = Field(..., description="事件类型: approval.created/approval.updated/approval.completed")
    approval_order_id: int = Field(..., description="审批单 ID")
    status: str | None = Field(None, description="审批单状态")
    timestamp: int = Field(..., description="事件时间戳")
    data: dict | None = Field(None, description="附加数据")


class WebhookResponse(BaseModel):
    """Webhook 响应"""
    received: bool = True
    event: str
    approval_order_id: int


# ==================== 路由 ====================

@router.post(
    "/approval-status",
    response_model=WebhookResponse,
    summary="审批状态变更回调",
    description="接收 OA 系统的审批状态变更通知，自动触发同步或审查。",
)
async def approval_status_webhook(
    request: Request,
    body: ApprovalStatusWebhook,
    db: AsyncSession = Depends(get_db),
):
    """审批状态变更 Webhook 回调

    验证签名后，根据事件类型触发相应操作：
    - approval.created → 同步审批单
    - approval.completed → 同步 + 自动审查
    """
    # 验证签名
    if not await _verify_signature(request):
        raise HTTPException(status_code=403, detail="签名校验失败")

    from loguru import logger

    logger.info(
        f"Webhook 收到 | event={body.event} | "
        f"approval_order_id={body.approval_order_id} | status={body.status}"
    )

    approval_service = ApprovalService(db)

    if body.event in ("approval.created", "approval.updated"):
        await approval_service.sync_approval(body.approval_order_id)

    if body.event == "approval.completed":
        await approval_service.sync_approval(body.approval_order_id)
        # 自动触发审查
        from app.workflow.contract_review_workflow import contract_review_workflow

        task_id = await contract_review_workflow.create_task(db, body.approval_order_id)
        await contract_review_workflow.run_background(task_id, body.approval_order_id)

    return WebhookResponse(
        received=True,
        event=body.event,
        approval_order_id=body.approval_order_id,
    )


@router.post(
    "/contract-uploaded",
    summary="合同附件上传回调",
    description="接收 OA 系统上传合同附件后的通知。",
)
async def contract_uploaded_webhook(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """合同附件上传 Webhook"""
    if not await _verify_signature(request):
        raise HTTPException(status_code=403, detail="签名校验失败")

    from loguru import logger

    approval_order_id = body.get("approval_order_id")
    logger.info(f"Webhook 合同上传 | approval_order_id={approval_order_id}")

    # 触发合同下载
    if approval_order_id:
        from app.services.contract.contract_service import ContractService

        contract_service = ContractService(db)
        await contract_service.download_attachment(approval_order_id)

    return {"received": True, "approval_order_id": approval_order_id}


# ==================== 签名校验 ====================

async def _verify_signature(request: Request) -> bool:
    """验证 Webhook 请求签名"""
    from app.core.config import settings

    # 开发环境跳过签名校验
    if settings.APP_DEBUG and not settings.OA_API_KEY:
        return True

    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        return False

    body = await request.body()
    secret = (settings.OA_API_KEY or "default_secret").encode("utf-8")
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


# ==================== 健康检查 ====================

@router.get(
    "/health",
    summary="Webhook 服务健康检查",
)
async def webhook_health():
    """Webhook 健康检查"""
    return {"status": "ok", "service": "webhook"}
