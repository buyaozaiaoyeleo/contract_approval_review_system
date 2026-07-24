"""OA 系统 HTTP 客户端"""

import hashlib
import hmac
import time

import httpx
from loguru import logger

from app.core.config import settings


class OAClient:
    """OA 审批系统 HTTP 客户端，封装与 OA 系统的所有交互"""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            # 使用连接池提升性能，配置超时限制防止长时间阻塞
            self._client = httpx.AsyncClient(
                base_url=settings.OA_BASE_URL,
                timeout=httpx.Timeout(settings.OA_TIMEOUT),
                headers=self._build_headers(),
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==================== 审批单 API ====================

    async def fetch_approval_detail(self, approval_id: str) -> dict | None:
        """拉取单个审批单详情"""
        try:
            response = await self.client.get(f"/api/approvals/{approval_id}")
            response.raise_for_status()
            data = response.json()
            logger.debug(f"OA 审批单拉取成功 | approval_id={approval_id}")
            return data.get("data") or data
        except httpx.HTTPStatusError as e:
            logger.error(f"OA 审批单拉取失败(HTTP {e.response.status_code}) | approval_id={approval_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"OA 审批单拉取失败(网络错误) | approval_id={approval_id} | error={e}")
            return None

    async def fetch_approval_list(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """分页拉取审批单列表"""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            response = await self.client.get("/api/approvals", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data") or data
        except Exception as e:
            logger.error(f"OA 审批单列表拉取失败 | page={page} | error={e}")
            raise

    # ==================== 评论 API ====================

    async def post_comment(self, approval_id: str, content: str, comment_id: str) -> bool:
        """回写审批评论到 OA 系统"""
        payload = {
            "approval_id": approval_id,
            "content": content,
            "comment_id": comment_id,
        }
        try:
            response = await self.client.post("/api/comments", json=payload)
            response.raise_for_status()
            logger.info(f"OA 评论回写成功 | approval_id={approval_id} | comment_id={comment_id}")
            return True
        except httpx.HTTPStatusError as e:
            # 409 Conflict 表示评论已存在（幂等），视为成功
            if e.response.status_code == 409:
                logger.info(f"OA 评论已存在(幂等) | approval_id={approval_id} | comment_id={comment_id}")
                return True
            logger.error(f"OA 评论回写失败(HTTP {e.response.status_code}) | approval_id={approval_id}")
            return False
        except Exception as e:
            logger.error(f"OA 评论回写失败 | approval_id={approval_id} | error={e}")
            return False

    # ==================== 附件下载 API ====================

    async def download_attachment(self, attachment_url: str) -> bytes | None:
        """下载审批单附件（合同文档）"""
        try:
            response = await self.client.get(attachment_url)
            response.raise_for_status()
            logger.debug(f"OA 附件下载成功 | url={attachment_url} | size={len(response.content)}")
            return response.content
        except Exception as e:
            logger.error(f"OA 附件下载失败 | url={attachment_url} | error={e}")
            return None

    # ==================== 签名与请求头 ====================

    def _build_headers(self) -> dict:
        """构建请求头，包含认证签名"""
        headers = {"Content-Type": "application/json"}
        if settings.OA_API_KEY:
            # 使用 HMAC-SHA256 签名
            timestamp = str(int(time.time()))
            sign = self._generate_sign(timestamp)
            headers["X-Api-Key"] = settings.OA_API_KEY
            headers["X-Timestamp"] = timestamp
            headers["X-Signature"] = sign
        return headers

    def _generate_sign(self, timestamp: str) -> str:
        """生成请求签名"""
        msg = f"{settings.OA_API_KEY}{timestamp}"
        return hmac.new(
            settings.OA_API_KEY.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


oa_client = OAClient()
