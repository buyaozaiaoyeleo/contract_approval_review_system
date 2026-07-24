"""审批单 Repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_order import ApprovalOrder
from app.repositories.base import BaseRepository


class ApprovalOrderRepository(BaseRepository[ApprovalOrder]):
    def __init__(self, db: AsyncSession):
        super().__init__(ApprovalOrder, db)

    async def get_by_approval_id(self, approval_id: str):
        return await self.get_by_field("approval_id", approval_id)

    async def upsert_by_approval_id(self, approval_id: str, **values) -> ApprovalOrder:
        existing = await self.get_by_approval_id(approval_id)
        if existing:
            for key, val in values.items():
                setattr(existing, key, val)
            return await self.update(existing)
        instance = ApprovalOrder(approval_id=approval_id, **values)
        return await self.create(instance)
