"""风险规则管理服务

提供风险规则的 CRUD 操作、分类查询、启用/禁用管理。
"""


from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.snowflake import generate_id
from app.models.risk_rule import RiskRule
from app.repositories.risk_rule_repo import RiskRuleRepository


class RuleService:
    """风险规则领域服务"""

    # 规则分类
    CATEGORIES = {
        "amount": "金额条款",
        "term": "期限条款",
        "clause": "通用条款",
        "subject": "主体资质",
        "compliance": "合规审查",
    }

    # 规则类型
    RULE_TYPES = {
        "field": "字段匹配",       # 基于合同字段值的规则
        "llm": "语义审查",        # 基于 LLM 的语义理解规则
        "composite": "复合规则",   # 字段 + LLM 组合
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RiskRuleRepository(db)

    # ==================== CRUD ====================

    async def create_rule(self, **kwargs) -> RiskRule:
        """创建风险规则"""
        rule = RiskRule(
            id=generate_id(),
            **kwargs,
        )
        result = await self.repo.create(rule)
        logger.info(f"风险规则已创建 | rule_code={result.rule_code} | name={result.rule_name}")
        return result

    async def update_rule(self, rule_id: int, **kwargs) -> RiskRule | None:
        """更新风险规则"""
        rule = await self.repo.get_by_id(rule_id)
        if not rule:
            return None
        for key, val in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, val)
        result = await self.repo.update(rule)
        logger.info(f"风险规则已更新 | rule_id={rule_id}")
        return result

    async def delete_rule(self, rule_id: int) -> bool:
        """删除风险规则"""
        result = await self.repo.delete_by_id(rule_id)
        if result:
            logger.info(f"风险规则已删除 | rule_id={rule_id}")
        return result

    async def toggle_rule(self, rule_id: int, enabled: bool) -> RiskRule | None:
        """启用/禁用风险规则"""
        rule = await self.repo.get_by_id(rule_id)
        if not rule:
            return None
        rule.is_enabled = enabled
        result = await self.repo.update(rule)
        logger.info(f"风险规则已{'启用' if enabled else '禁用'} | rule_id={rule_id}")
        return result

    # ==================== 查询 ====================

    async def get_rule(self, rule_id: int) -> RiskRule | None:
        """按 ID 查询规则"""
        return await self.repo.get_by_id(rule_id)

    async def get_by_rule_code(self, rule_code: str) -> RiskRule | None:
        """按规则编码查询"""
        return await self.repo.get_by_rule_code(rule_code)

    async def list_all(self, enabled_only: bool = True) -> list[RiskRule]:
        """列出所有规则"""
        if enabled_only:
            return await self.repo.list_enabled()
        return await self.repo.get_all(limit=1000)

    async def list_by_category(self, category: str) -> list[RiskRule]:
        """按分类列出规则"""
        return await self.repo.list_by_category(category)

    async def list_enabled(self) -> list[RiskRule]:
        """列出所有启用的规则（按优先级排序）"""
        return await self.repo.list_enabled()

    # ==================== 批量查询（供引擎调用） ====================

    async def get_rules_by_category(self, categories: list[str]) -> list[RiskRule]:
        """按多个分类获取启用的规则"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(self.repo.model)
            .where(
                self.repo.model.rule_category.in_(categories),
                self.repo.model.is_enabled,
            )
            .order_by(self.repo.model.priority.desc())
        )
        return list(result.scalars().all())

    async def get_rules_by_type(self, rule_type: str) -> list[RiskRule]:
        """按规则类型获取启用的规则"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(self.repo.model)
            .where(
                self.repo.model.rule_type == rule_type,
                self.repo.model.is_enabled,
            )
            .order_by(self.repo.model.priority.desc())
        )
        return list(result.scalars().all())


# ==================== 服务工厂 ====================

def get_rule_service(db: AsyncSession) -> RuleService:
    """获取规则管理服务实例"""
    return RuleService(db)
