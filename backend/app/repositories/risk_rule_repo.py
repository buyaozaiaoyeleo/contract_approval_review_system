"""风险规则 Repository"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_rule import RiskRule
from app.repositories.base import BaseRepository


class RiskRuleRepository(BaseRepository[RiskRule]):
    def __init__(self, db: AsyncSession):
        super().__init__(RiskRule, db)

    async def get_by_rule_code(self, rule_code: str):
        return await self.get_by_field("rule_code", rule_code)

    async def list_enabled(self):
        result = await self.db.execute(
            select(self.model).where(self.model.is_enabled).order_by(self.model.priority.desc())
        )
        return list(result.scalars().all())

    async def list_by_category(self, category: str):
        result = await self.db.execute(
            select(self.model).where(self.model.rule_category == category, self.model.is_enabled)
        )
        return list(result.scalars().all())
