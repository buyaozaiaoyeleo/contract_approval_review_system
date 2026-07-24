"""审批评论 Repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_comment import ApprovalComment
from app.repositories.base import BaseRepository


class ApprovalCommentRepository(BaseRepository[ApprovalComment]):
    def __init__(self, db: AsyncSession):
        super().__init__(ApprovalComment, db)

    async def get_by_comment_id(self, comment_id: str):
        return await self.get_by_field("comment_id", comment_id)

    async def list_by_approval_order(self, approval_order_id: int) -> list[ApprovalComment]:
        """按审批单 ID 查询所有评论"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(self.model)
            .where(self.model.approval_order_id == approval_order_id)
            .order_by(self.model.created_at.asc())
        )
        return list(result.scalars().all())
