"""风险规则匹配引擎单元测试"""


import pytest

from app.models.contract_field import ContractField
from app.models.risk_rule import RiskRule
from app.services.risk.risk_engine import RiskEngine


class TestRiskEngine:
    """风险规则匹配引擎测试"""

    @pytest.fixture
    def engine(self) -> RiskEngine:
        return RiskEngine()

    @pytest.fixture
    def sample_fields(self) -> ContractField:
        """创建测试合同字段"""
        return ContractField(
            contract_no="HT-2024-0001",
            party_a_info='{"name":"甲方科技","address":"北京"}',
            party_b_info='{"name":"乙方信息","address":"上海"}',
            amount="500000元",
            start_date="2024-01-01",
            end_date="2024-12-31",
            payment_terms="合同签订后30日内支付50%",
            liability_clause="违约方支付20%违约金",
            confidentiality="保密期限5年",
            dispute_resolution="向甲方所在地法院诉讼",
            extract_confidence=0.92,
        )

    @pytest.fixture
    def make_rule(self):
        """创建规则工厂"""
        def _make(**kwargs):
            defaults = {
                "id": 1,
                "rule_code": "TEST_RULE",
                "rule_name": "测试规则",
                "rule_category": "clause",
                "rule_type": "field",
                "rule_config_json": "{}",
                "priority": 1,
                "risk_level": "MEDIUM",
                "is_enabled": True,
                "description": "测试",
            }
            defaults.update(kwargs)
            return RiskRule(**defaults)
        return _make

    # ==================== 字段匹配测试 ====================

    @pytest.mark.asyncio
    async def test_contains_match(self, engine, sample_fields, make_rule):
        """测试关键词包含匹配"""
        rule = make_rule(
            rule_code="PAYMENT_CHECK",
            rule_config_json='{"field":"payment_terms","match_type":"contains","keywords":["支付50%"]}',
            risk_level="MEDIUM",
        )

        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is not None
        assert result["risk_level"] == "MEDIUM"
        assert "支付50%" in result["source_text"]

    @pytest.mark.asyncio
    async def test_contains_no_match(self, engine, sample_fields, make_rule):
        """测试关键词不匹配"""
        rule = make_rule(
            rule_code="PAYMENT_CHECK",
            rule_config_json='{"field":"payment_terms","match_type":"contains","keywords":["一次性付清"]}',
        )

        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is None

    @pytest.mark.asyncio
    async def test_regex_match(self, engine, sample_fields, make_rule):
        """测试正则匹配"""
        rule = make_rule(
            rule_code="CONTRACT_NO_CHECK",
            rule_config_json='{"field":"contract_no","match_type":"regex","pattern":"HT-\\\\d{4}-\\\\d{4}"}',
        )

        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is not None

    @pytest.mark.asyncio
    async def test_missing_field_check(self, engine, sample_fields, make_rule):
        """测试缺失字段检查"""
        # 字段存在
        rule = make_rule(
            rule_code="LIABILITY_CHECK",
            rule_config_json='{"field":"liability_clause","match_type":"missing"}',
        )

        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is None

        # 字段缺失
        sample_fields.liability_clause = None
        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is not None

    @pytest.mark.asyncio
    async def test_range_check(self, engine, sample_fields, make_rule):
        """测试数值范围检查"""
        # 金额低于最低阈值 → 触发风险（500000 < 1000000）
        rule = make_rule(
            rule_code="AMOUNT_CHECK",
            rule_config_json='{"field":"amount","match_type":"range","min":1000000}',
            risk_level="HIGH",
        )

        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is not None
        assert result["risk_level"] == "HIGH"

        # 金额高于最低阈值 → 不触发风险（2000000 >= 1000000）
        sample_fields.amount = "2000000元"
        result = await engine._evaluate_field_rule(rule, sample_fields)
        assert result is None

        # 超出上限也触发风险
        rule2 = make_rule(
            rule_code="AMOUNT_CEILING",
            rule_config_json='{"field":"amount","match_type":"range","max":1000000}',
            risk_level="MEDIUM",
        )
        result = await engine._evaluate_field_rule(rule2, sample_fields)
        assert result is not None
        assert result["risk_level"] == "MEDIUM"

    # ==================== 综合评分测试 ====================

    def test_calculate_risk_score_high(self, engine):
        """测试综合评分 - 高风险"""
        results = [
            {"risk_level": "HIGH", "risk_description": "风险1"},
            {"risk_level": "HIGH", "risk_description": "风险2"},
            {"risk_level": "MEDIUM", "risk_description": "风险3"},
        ]

        score = engine.calculate_risk_score(results)
        assert score["overall_level"] == "HIGH"
        assert score["high_count"] == 2
        assert score["score"] == 8  # 2*3 + 1*2

    def test_calculate_risk_score_medium(self, engine):
        """测试综合评分 - 中风险"""
        results = [
            {"risk_level": "HIGH", "risk_description": "风险1"},
            {"risk_level": "MEDIUM", "risk_description": "风险2"},
        ]

        score = engine.calculate_risk_score(results)
        assert score["overall_level"] == "MEDIUM"
        assert score["score"] == 5  # 1*3 + 1*2

    def test_calculate_risk_score_low(self, engine):
        """测试综合评分 - 低风险"""
        results = [
            {"risk_level": "LOW", "risk_description": "风险1"},
            {"risk_level": "LOW", "risk_description": "风险2"},
        ]

        score = engine.calculate_risk_score(results)
        assert score["overall_level"] == "LOW"
        assert score["score"] == 2  # 2*1

    def test_calculate_risk_score_none(self, engine):
        """测试综合评分 - 无风险"""
        score = engine.calculate_risk_score([])
        assert score["overall_level"] == "NONE"
        assert score["total_count"] == 0

    # ==================== 配置解析测试 ====================

    def test_parse_valid_config(self, engine):
        """测试解析有效 JSON 配置"""
        config = engine._parse_config('{"field":"amount","match_type":"range","min":1000000}')
        assert config["field"] == "amount"
        assert config["min"] == 1000000

    def test_parse_invalid_config(self, engine):
        """测试解析无效 JSON 配置"""
        config = engine._parse_config("invalid json")
        assert config == {}

    def test_parse_none_config(self, engine):
        """测试解析 None 配置"""
        config = engine._parse_config(None)
        assert config == {}

    # ==================== 上下文提取测试 ====================

    def test_extract_context(self, engine):
        """测试关键词上下文提取"""
        text = "本合同签订后30日内，甲方向乙方支付合同总额的50%作为首付款。"
        keyword = "支付"
        context = engine._extract_context(text, keyword)
        assert keyword in context
        assert len(context) <= len(keyword) + 80

    def test_extract_context_not_found(self, engine):
        """测试关键词不存在时返回原文"""
        context = engine._extract_context("合同文本", "不存在的关键词")
        assert context == "不存在的关键词"

    # ==================== LLM 审查测试 ====================

    @pytest.mark.asyncio
    async def test_llm_rule_no_text(self, engine, make_rule):
        """测试 LLM 审查无文本时返回 None"""
        rule = make_rule(
            rule_code="LLM_CHECK",
            rule_type="llm",
            rule_config_json='{"field":"dispute_resolution","prompt":"检查争议解决条款"}',
        )

        result = await engine._evaluate_llm_rule(rule, "")
        assert result is None
