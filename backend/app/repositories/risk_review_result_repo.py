"""风险结果 Repository"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_review_result import RiskReviewResult
from app.repositories.base import BaseRepository


class RiskReviewResultRepository(BaseRepository[RiskReviewResult]):
    def __init__(self, db: AsyncSession):
        super().__init__(RiskReviewResult, db)

    async def list_by_approval_order(self, approval_order_id: int):
        result = await self.db.execute(
            select(self.model)
            .where(self.model.approval_order_id == approval_order_id)
            .order_by(self.model.created_at.asc(), self.model.id.asc())
        )
        return list(result.scalars().all())

    async def get_by_risk_id(self, risk_id: str):
        return await self.get_by_field("risk_id", risk_id)

    async def delete_by_approval_order(self, approval_order_id: int) -> None:
        await self.db.execute(
            delete(self.model).where(self.model.approval_order_id == approval_order_id)
        )
        await self.db.flush()
