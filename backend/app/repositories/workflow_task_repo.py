"""工作流任务 Repository"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_task import WorkflowTask
from app.repositories.base import BaseRepository


class WorkflowTaskRepository(BaseRepository[WorkflowTask]):
    def __init__(self, db: AsyncSession):
        super().__init__(WorkflowTask, db)

    async def get_by_task_id(self, task_id: str):
        return await self.get_by_field("task_id", task_id)

    async def list_by_status(self, status: str, limit: int = 100):
        result = await self.db.execute(
            select(self.model).where(self.model.status == status).limit(limit)
        )
        return list(result.scalars().all())

    async def get_running_by_approval(self, approval_order_id: int):
        result = await self.db.execute(
            select(self.model).where(
                self.model.approval_order_id == approval_order_id,
                self.model.status.in_(["pending", "running"]),
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_by_approval(self, approval_order_id: int):
        result = await self.db.execute(
            select(self.model)
            .where(self.model.approval_order_id == approval_order_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return result.scalars().first()
