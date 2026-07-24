"""风险规则管理服务单元测试"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.risk.rule_service import RuleService


class TestRuleService:
    """风险规则管理服务测试"""

    @pytest.mark.asyncio
    async def test_create_rule(self, db_session: AsyncSession):
        """测试创建风险规则"""
        service = RuleService(db_session)
        rule = await service.create_rule(
            rule_code="TEST_RULE_001",
            rule_name="测试规则",
            rule_category="amount",
            rule_type="field",
            rule_config_json='{"field":"amount","match_type":"range","min":1000000}',
            priority=10,
            risk_level="HIGH",
            description="测试规则描述",
        )

        assert rule.rule_code == "TEST_RULE_001"
        assert rule.rule_name == "测试规则"
        assert rule.is_enabled is True

    @pytest.mark.asyncio
    async def test_get_by_rule_code(self, db_session: AsyncSession):
        """测试按规则编码查询"""
        service = RuleService(db_session)
        await service.create_rule(
            rule_code="TEST_RULE_002",
            rule_name="测试规则2",
            rule_category="clause",
            rule_type="field",
            rule_config_json="{}",
            priority=5,
            risk_level="MEDIUM",
        )

        rule = await service.get_by_rule_code("TEST_RULE_002")
        assert rule is not None
        assert rule.rule_name == "测试规则2"

    @pytest.mark.asyncio
    async def test_update_rule(self, db_session: AsyncSession):
        """测试更新规则"""
        service = RuleService(db_session)
        created = await service.create_rule(
            rule_code="TEST_RULE_003",
            rule_name="更新前",
            rule_category="clause",
            rule_type="field",
            rule_config_json="{}",
            priority=5,
            risk_level="LOW",
        )

        updated = await service.update_rule(created.id, rule_name="更新后", risk_level="HIGH")
        assert updated is not None
        assert updated.rule_name == "更新后"
        assert updated.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_toggle_rule(self, db_session: AsyncSession):
        """测试启用/禁用规则"""
        service = RuleService(db_session)
        created = await service.create_rule(
            rule_code="TEST_RULE_004",
            rule_name="开关规则",
            rule_category="compliance",
            rule_type="field",
            rule_config_json="{}",
            priority=1,
            risk_level="LOW",
        )

        disabled = await service.toggle_rule(created.id, enabled=False)
        assert disabled is not None
        assert disabled.is_enabled is False

        enabled = await service.toggle_rule(created.id, enabled=True)
        assert enabled.is_enabled is True

    @pytest.mark.asyncio
    async def test_delete_rule(self, db_session: AsyncSession):
        """测试删除规则"""
        service = RuleService(db_session)
        created = await service.create_rule(
            rule_code="TEST_RULE_005",
            rule_name="待删除",
            rule_category="compliance",
            rule_type="field",
            rule_config_json="{}",
            priority=1,
            risk_level="LOW",
        )

        result = await service.delete_rule(created.id)
        assert result is True

        deleted = await service.get_rule(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_list_by_category(self, db_session: AsyncSession):
        """测试按分类查询"""
        service = RuleService(db_session)
        await service.create_rule(
            rule_code="CAT_AMOUNT_1",
            rule_name="金额规则",
            rule_category="amount",
            rule_type="field",
            rule_config_json="{}",
            priority=5,
            risk_level="MEDIUM",
        )
        await service.create_rule(
            rule_code="CAT_CLAUSE_1",
            rule_name="条款规则",
            rule_category="clause",
            rule_type="field",
            rule_config_json="{}",
            priority=5,
            risk_level="MEDIUM",
        )

        amount_rules = await service.list_by_category("amount")
        assert len(amount_rules) == 1
        assert amount_rules[0].rule_code == "CAT_AMOUNT_1"

    @pytest.mark.asyncio
    async def test_list_enabled(self, db_session: AsyncSession):
        """测试列出启用的规则（按优先级排序）"""
        service = RuleService(db_session)
        await service.create_rule(
            rule_code="PRIO_LOW",
            rule_name="低优先级",
            rule_category="clause",
            rule_type="field",
            rule_config_json="{}",
            priority=1,
            risk_level="LOW",
        )
        await service.create_rule(
            rule_code="PRIO_HIGH",
            rule_name="高优先级",
            rule_category="clause",
            rule_type="field",
            rule_config_json="{}",
            priority=10,
            risk_level="HIGH",
        )

        rules = await service.list_enabled()
        assert len(rules) >= 2
        # 高优先级排在前面
        assert rules[0].priority >= rules[1].priority
