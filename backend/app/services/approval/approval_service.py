"""Approval domain service."""

from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.oa_client import oa_client
from app.common.snowflake import generate_id
from app.models.approval_comment import ApprovalComment
from app.models.approval_order import ApprovalOrder
from app.models.contract_document import ContractDocument
from app.repositories.approval_comment_repo import ApprovalCommentRepository
from app.repositories.approval_order_repo import ApprovalOrderRepository
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.repositories.workflow_task_repo import WorkflowTaskRepository


class ApprovalService:
    """Approval-related coordination service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = ApprovalOrderRepository(db)
        self.comment_repo = ApprovalCommentRepository(db)
        self.doc_repo = ContractDocumentRepository(db)
        self.task_repo = WorkflowTaskRepository(db)

    async def sync_approval(self, approval_id: str) -> ApprovalOrder | None:
        """Sync one approval from OA, or fall back to an existing local order."""
        existing_order = await self._resolve_order(approval_id)
        oa_lookup_id = existing_order.approval_id if existing_order else approval_id

        oa_data = await oa_client.fetch_approval_detail(oa_lookup_id)
        if oa_data is None:
            if existing_order:
                logger.warning(
                    "OA sync unavailable, keep local approval | approval_id={} | local_order_id={}",
                    approval_id,
                    existing_order.id,
                )
                return existing_order

            logger.warning("OA approval sync failed | approval_id={}", approval_id)
            return None

        order = await self.order_repo.upsert_by_approval_id(
            approval_id=oa_lookup_id,
            title=oa_data.get("title", ""),
            status=oa_data.get("status", "pending"),
            applicant=oa_data.get("applicant", ""),
            department=oa_data.get("department", ""),
            oa_created_at=self._parse_oa_datetime(oa_data.get("created_at")),
            raw_data=str(oa_data),
        )
        logger.info("Approval synced | approval_id={} | status={}", oa_lookup_id, order.status)
        return order

    async def batch_sync(self, page: int = 1, page_size: int = 50) -> list[ApprovalOrder]:
        """Batch sync approvals from OA."""
        oa_result = await oa_client.fetch_approval_list(page=page, page_size=page_size)
        items = oa_result.get("items", []) if isinstance(oa_result, dict) else []

        orders: list[ApprovalOrder] = []
        for item in items:
            approval_id = item.get("approval_id") or item.get("id")
            if not approval_id:
                continue

            order = await self.order_repo.upsert_by_approval_id(
                approval_id=str(approval_id),
                title=item.get("title", ""),
                status=item.get("status", "pending"),
                applicant=item.get("applicant", ""),
                department=item.get("department", ""),
                oa_created_at=self._parse_oa_datetime(item.get("created_at")),
                raw_data=str(item),
            )
            orders.append(order)

        logger.info("Batch approval sync completed | count={} | page={}", len(orders), page)
        return orders

    async def get_by_approval_id(self, approval_id: str) -> ApprovalOrder | None:
        return await self.order_repo.get_by_approval_id(approval_id)

    async def get_by_id(self, order_id: int) -> ApprovalOrder | None:
        return await self.order_repo.get_by_id(order_id)

    async def get_approval(self, approval_order_id: int) -> ApprovalOrder | None:
        return await self.order_repo.get_by_id(approval_order_id)

    async def refresh_order_status_from_workflow(self, approval_order_id: int) -> ApprovalOrder | None:
        order = await self.order_repo.get_by_id(approval_order_id)
        if not order:
            return None

        latest_task = await self.task_repo.get_latest_by_approval(approval_order_id)
        if not latest_task:
            return order

        status_map = {
            "pending": "reviewing",
            "running": "reviewing",
            "success": "reviewed",
            "failed": "rejected",
            "blocked": "rejected",
            "cancelled": "rejected",
        }
        mapped_status = status_map.get(latest_task.status, order.status)
        if order.status != mapped_status:
            order.status = mapped_status
            await self.order_repo.update(order)
            logger.info(
                "Approval status refreshed from workflow | approval_order_id={} | workflow_status={} | approval_status={}",
                approval_order_id,
                latest_task.status,
                mapped_status,
            )
        return order

    async def get_documents(self, approval_order_id: int) -> list[ContractDocument]:
        return await self.doc_repo.list_by_approval_order(approval_order_id)

    async def get_comments(self, approval_order_id: int):
        return await self.comment_repo.list_by_approval_order(approval_order_id)

    async def write_comment(
        self,
        approval_id: str | int,
        content: str,
        risk_level: str | None = None,
        risk_summary: str | None = None,
    ) -> ApprovalComment | None:
        """Write one AI comment back to OA and persist locally."""
        order = await self._resolve_order(approval_id)
        if not order:
            logger.error("Comment write failed, approval not found | approval_id={}", approval_id)
            return None

        oa_approval_id = order.approval_id
        comment_id = f"{oa_approval_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        success = await oa_client.post_comment(oa_approval_id, content, comment_id)
        if not success:
            logger.error("OA comment write failed | approval_id={}", oa_approval_id)
            return None

        comment = await self.comment_repo.create(
            ApprovalComment(
                id=generate_id(),
                comment_id=comment_id,
                approval_order_id=order.id,
                content=content,
                risk_level=risk_level,
                risk_summary=risk_summary,
                is_ai_generated=True,
            )
        )
        logger.info("Comment write completed | approval_id={} | comment_id={}", oa_approval_id, comment_id)
        return comment

    async def ensure_order_for_document(self, doc_id: str, title: str) -> ApprovalOrder:
        """Create a local approval order for direct document review if needed."""
        existing = await self.order_repo.get_by_approval_id(f"REVIEW_{doc_id}")
        if existing:
            return existing

        order = ApprovalOrder(
            id=generate_id(),
            approval_id=f"REVIEW_{doc_id}",
            title=title,
            status="reviewing",
            applicant="",
            department="",
        )
        await self.order_repo.create(order)
        return order

    @staticmethod
    def _parse_oa_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    async def _resolve_order(self, approval_id: str | int) -> ApprovalOrder | None:
        if isinstance(approval_id, int):
            return await self.order_repo.get_by_id(approval_id)

        approval_text = str(approval_id)
        if approval_text.isdigit():
            order = await self.order_repo.get_by_id(int(approval_text))
            if order:
                return order

        return await self.order_repo.get_by_approval_id(approval_text)


def get_approval_service(db: AsyncSession) -> ApprovalService:
    return ApprovalService(db)
