"""API 依赖注入

提供 FastAPI 路由中常用的依赖项：
- get_db: 数据库会话注入
- get_redis: Redis 客户端注入
- 各业务服务工厂函数
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.infrastructure.redis_client import RedisClient, redis_client

# ==================== 数据库会话 ====================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（FastAPI 依赖注入）

    使用 yield 确保请求结束后自动关闭会话。
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ==================== Redis 客户端 ====================

async def get_redis() -> RedisClient:
    """获取 Redis 客户端"""
    return redis_client


# ==================== 认证依赖 ====================

async def verify_api_key(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> str:
    """验证请求认证（支持 X-API-Key 或 Bearer Token）

    优先级：
    1. OA_API_KEY 未配置 → 放行
    2. X-API-Key Header 有效 → 放行
    3. Authorization Bearer Token 有效 → 放行
    4. 否则返回 401
    """
    from app.core.config import settings

    # 未配置 OA_API_KEY 则跳过认证
    if not settings.OA_API_KEY:
        return "anonymous"

    # 优先检查 X-API-Key
    if x_api_key and x_api_key == settings.OA_API_KEY:
        return "authenticated"

    # 其次检查 Authorization Bearer Token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        from app.core.security import verify_token
        payload = verify_token(token)
        if payload:
            return "authenticated"

    # 两者都没有或都无效
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请提供有效的 X-API-Key 或 Bearer Token",
    )


async def verify_webhook_signature(request: Request) -> bool:
    """验证 Webhook 请求签名

    从请求头中提取签名并与本地计算值比对。
    """
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Webhook 签名",
        )

    body = await request.body()
    if not _verify_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook 签名校验失败",
        )

    return True


def _verify_signature(body: bytes, signature: str) -> bool:
    """SHA256-HMAC 签名校验"""
    import hashlib
    import hmac

    from app.core.config import settings

    secret = (settings.OA_API_KEY or "default_secret").encode("utf-8")
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


# ==================== 业务服务工厂 ====================

async def get_approval_service(db: AsyncSession = Depends(get_db)):
    """获取审批单服务"""
    from app.services.approval.approval_service import ApprovalService
    return ApprovalService(db)


async def get_contract_service(db: AsyncSession = Depends(get_db)):
    """获取合同服务"""
    from app.services.contract.contract_service import ContractService
    return ContractService(db)


async def get_parser_service(db: AsyncSession = Depends(get_db)):
    """获取文档解析服务"""
    from app.services.parser.parser_service import DocumentParserService
    return DocumentParserService(db)


async def get_risk_review_service(db: AsyncSession = Depends(get_db)):
    """获取风险审查服务"""
    from app.services.risk.risk_service import RiskReviewService
    return RiskReviewService(db)


async def get_rule_service(db: AsyncSession = Depends(get_db)):
    """获取风险规则服务"""
    from app.services.risk.rule_service import RuleService
    return RuleService(db)
