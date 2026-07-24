"""风险规则匹配引擎

负责将合同字段与风险规则进行匹配，支持三种匹配模式：
- field: 基于字段值的规则匹配（正则/关键词/范围）
- llm: 基于 LLM 语义理解的审查
- composite: 字段 + LLM 组合审查
"""

import json
import re

from loguru import logger

from app.models.contract_field import ContractField
from app.models.risk_rule import RiskRule


class RiskEngine:
    """风险规则匹配引擎"""

    # 风险等级权重（用于综合评分）
    LEVEL_WEIGHTS = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    # ==================== 引擎入口 ====================

    async def evaluate(
        self,
        rules: list[RiskRule],
        contract_fields: ContractField,
        contract_text: str = "",
    ) -> list[dict]:
        """评估所有规则，返回风险结果列表"""
        results = []

        for rule in rules:
            try:
                result = await self._evaluate_rule(rule, contract_fields, contract_text)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"规则评估异常 | rule_code={rule.rule_code} | error={e}")
                continue

        # 按风险等级排序（高→低）
        results.sort(key=lambda r: self.LEVEL_WEIGHTS.get(r["risk_level"], 0), reverse=True)
        logger.info(f"规则评估完成 | total_rules={len(rules)} | matched={len(results)}")
        return results

    async def _evaluate_rule(
        self,
        rule: RiskRule,
        contract_fields: ContractField,
        contract_text: str,
    ) -> dict | None:
        """评估单条规则，匹配则返回风险结果"""
        rule_type = rule.rule_type

        if rule_type == "field":
            return await self._evaluate_field_rule(rule, contract_fields)
        elif rule_type == "llm":
            return await self._evaluate_llm_rule(rule, contract_text)
        elif rule_type == "composite":
            return await self._evaluate_composite_rule(rule, contract_fields, contract_text)
        else:
            logger.warning(f"未知规则类型 | rule_type={rule_type}")
            return None

    # ==================== 字段匹配规则 ====================

    async def _evaluate_field_rule(
        self, rule: RiskRule, contract_fields: ContractField
    ) -> dict | None:
        """基于字段值的规则匹配"""
        config = self._parse_config(rule.rule_config_json)
        if not config:
            return None

        field_name = config.get("field", "")
        field_value = getattr(contract_fields, field_name, None)
        match_type = config.get("match_type", "contains")

        # 缺失检查：优先处理，不受 field_value 是否为 None 影响
        if match_type == "missing":
            if field_value is None or str(field_value).strip() == "":
                return self._build_result(rule, "", field_name, config.get("description"))
            return None

        # 字段值为空但非缺失检查 → 无匹配
        if field_value is None:
            return None

        matched = False
        source_text = ""

        if match_type == "contains":
            # 关键词包含匹配
            keywords = config.get("keywords", [])
            field_str = str(field_value)
            for kw in keywords:
                if kw in field_str:
                    matched = True
                    source_text = self._extract_context(field_str, kw)
                    break

        elif match_type == "regex":
            # 正则匹配
            pattern = config.get("pattern", "")
            if pattern:
                match = re.search(pattern, str(field_value), re.IGNORECASE)
                if match:
                    matched = True
                    source_text = match.group(0)

        elif match_type == "range":
            # 数值范围检查：值低于 min 或高于 max 时触发风险
            try:
                value = float(str(field_value).replace(",", "").replace("元", ""))
                min_val = config.get("min")
                max_val = config.get("max")
                if min_val is not None and value < min_val:
                    matched = True
                if max_val is not None and value > max_val:
                    matched = True
            except (ValueError, TypeError):
                pass

        if matched:
            return self._build_result(rule, source_text, field_name, config.get("description"))
        return None

    # ==================== LLM 语义审查规则 ====================

    async def _evaluate_llm_rule(
        self, rule: RiskRule, contract_text: str
    ) -> dict | None:
        """基于 LLM 的语义审查"""
        if not contract_text:
            return None

        config = self._parse_config(rule.rule_config_json)
        if not config:
            return None

        try:
            from openai import AsyncOpenAI

            from app.core.config import settings

            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY.get_secret_value(),
                base_url=settings.LLM_BASE_URL,
            )

            review_prompt = config.get("prompt", rule.description)
            field_name = config.get("field", "")

            prompt = f"""请审查以下合同文本，判断是否存在风险。

审查规则：{review_prompt}

合同文本：
{contract_text[:8000]}

请以 JSON 格式返回：
{{
    "has_risk": true/false,
    "risk_level": "HIGH/MEDIUM/LOW/NONE",
    "risk_description": "风险描述",
    "suggestion": "修改建议",
    "source_text": "原文相关段落"
}}
"""
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=min(settings.LLM_MAX_TOKENS, 2048),
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            llm_result = json.loads(content)

            if llm_result.get("has_risk"):
                return self._build_result(
                    rule,
                    llm_result.get("source_text", ""),
                    field_name,
                    llm_result.get("risk_description", ""),
                    llm_result.get("suggestion", ""),
                )
            return None

        except ImportError:
            logger.warning("openai 未安装，LLM 审查跳过")
            return None
        except Exception as e:
            logger.error(f"LLM 审查失败 | rule_code={rule.rule_code} | error={e}")
            return None

    # ==================== 复合规则 ====================

    async def _evaluate_composite_rule(
        self,
        rule: RiskRule,
        contract_fields: ContractField,
        contract_text: str,
    ) -> dict | None:
        """复合规则：先字段匹配，再 LLM 审查"""
        # 先执行字段匹配
        field_result = await self._evaluate_field_rule(rule, contract_fields)
        if not field_result:
            return None

        # 再执行 LLM 语义审查
        llm_result = await self._evaluate_llm_rule(rule, contract_text)
        if llm_result:
            # 以 LLM 结果为准，覆盖字段匹配
            return llm_result

        return field_result

    # ==================== 工具方法 ====================

    def _parse_config(self, config_json: str | None) -> dict:
        """解析规则配置 JSON"""
        if not config_json:
            return {}
        try:
            return json.loads(config_json)
        except json.JSONDecodeError:
            return {}

    def _build_result(
        self,
        rule: RiskRule,
        source_text: str = "",
        field_name: str = "",
        description: str = "",
        suggestion: str = "",
    ) -> dict:
        """构建风险结果"""
        return {
            "rule_id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "rule_category": rule.rule_category,
            "risk_level": rule.risk_level,
            "risk_description": description or rule.description or rule.rule_name,
            "suggestion": suggestion or f"请关注{rule.rule_name}相关条款",
            "source_text": source_text,
            "field_name": field_name,
        }

    @staticmethod
    def _extract_context(text: str, keyword: str, context_chars: int = 80) -> str:
        """提取关键词上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return keyword
        start = max(0, idx - context_chars // 2)
        end = min(len(text), idx + len(keyword) + context_chars // 2)
        return text[start:end]

    # ==================== 综合评分 ====================

    def calculate_risk_score(self, results: list[dict]) -> dict:
        """计算综合风险评分"""
        high_count = sum(1 for r in results if r["risk_level"] == "HIGH")
        medium_count = sum(1 for r in results if r["risk_level"] == "MEDIUM")
        low_count = sum(1 for r in results if r["risk_level"] == "LOW")

        # 加权评分
        score = (
            high_count * self.LEVEL_WEIGHTS["HIGH"]
            + medium_count * self.LEVEL_WEIGHTS["MEDIUM"]
            + low_count * self.LEVEL_WEIGHTS["LOW"]
        )

        # 综合等级判定
        if high_count >= 2:
            overall_level = "HIGH"
        elif high_count >= 1 or medium_count >= 3:
            overall_level = "MEDIUM"
        elif medium_count >= 1 or low_count >= 2:
            overall_level = "LOW"
        else:
            overall_level = "NONE"

        return {
            "overall_level": overall_level,
            "score": score,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "total_count": len(results),
        }


    # ==================== 全面 LLM 审核 ====================

    async def comprehensive_llm_review(
        self, contract_text: str, field_data: dict | None = None
    ) -> list[dict]:
        """使用 LLM 对合同进行全面语义审核

        不依赖单条规则，而是将整份合同发给 LLM，一次识别所有风险点。
        返回结构化风险列表，与规则引擎输出格式一致。
        """
        if not contract_text or len(contract_text.strip()) < 50:
            logger.warning("合同文本过短，跳过 LLM 全面审核")
            return []

        try:
            from openai import AsyncOpenAI
            from app.core.config import settings
        except ImportError:
            logger.warning("openai 未安装，跳过 LLM 全面审核")
            return []

        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY.get_secret_value(),
            base_url=settings.LLM_BASE_URL,
        )

        # 截断过长文本（保留开头 + 关键中间 + 结尾）
        text = self._truncate_for_llm(contract_text, max_chars=12000)

        # 构建字段摘要
        field_summary = ""
        if field_data:
            field_summary = f"""
已提取的合同关键字段：
- 合同编号: {field_data.get('contract_no', '未提取')}
- 甲方: {field_data.get('party_a_info', '未提取')}
- 乙方: {field_data.get('party_b_info', '未提取')}
- 合同金额: {field_data.get('amount', '未提取')}
- 开始日期: {field_data.get('start_date', '未提取')}
- 结束日期: {field_data.get('end_date', '未提取')}
- 付款条款: {field_data.get('payment_terms', '未提取')}
- 违约责任: {field_data.get('liability_clause', '未提取')}
"""

        prompt = f"""你是一位资深的合同审核律师。请对以下合同进行全面风险审核，识别所有潜在风险点。

{field_summary}

请从以下维度逐一审查：

1. **金额与支付**：金额是否明确？付款条件是否合理？是否存在资金风险？
2. **履约期限**：合同期限是否明确？是否存在无限期履约风险？
3. **违约责任**：违约条款是否对等？是否存在过重或缺失的违约责任？
4. **知识产权与保密**：IP 归属是否清晰？保密义务是否充分？
5. **争议解决**：争议解决方式是否明确？管辖地是否有利？
6. **合同完整性**：是否缺少关键条款（验收标准、售后服务、不可抗力等）？
7. **合规风险**：是否存在违反法律法规的条款？

合同文本：
{text}

请按以下 JSON 格式返回（只返回 JSON，不要其他内容）：
{{
    "overall_assessment": {{
        "risk_level": "HIGH/MEDIUM/LOW/NONE",
        "summary": "一句话总结整体风险状况",
        "score": 0-100
    }},
    "risks": [
        {{
            "risk_category": "amount/term/clause/subject/compliance",
            "risk_level": "HIGH/MEDIUM/LOW",
            "risk_name": "风险名称（简短）",
            "risk_description": "详细风险说明",
            "suggestion": "修改建议",
            "source_text": "合同中相关原文（摘录关键句）"
        }}
    ]
}}

注意：
- 只报告真实存在的风险，不要虚构
- source_text 必须是合同原文中的真实语句
- 如果某个维度没有风险，就不要在 risks 中包含"""
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=min(settings.LLM_MAX_TOKENS, 4096),
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # 转换为标准风险结果格式
            risks = []
            for r in result.get("risks", []):
                risks.append({
                    "rule_id": None,                     # LLM 审核不关联具体规则
                    "rule_code": "LLM_COMPREHENSIVE",
                    "rule_name": r.get("risk_name", "LLM 审核风险"),
                    "rule_category": r.get("risk_category", "clause"),
                    "risk_level": r.get("risk_level", "MEDIUM"),
                    "risk_description": r.get("risk_description", ""),
                    "suggestion": r.get("suggestion", ""),
                    "source_text": r.get("source_text", ""),
                    "field_name": "",
                })

            logger.info(
                f"LLM 全面审核完成 | risks_found={len(risks)} "
                f"| overall={result.get('overall_assessment', {}).get('risk_level', 'NONE')}"
            )
            return risks

        except Exception as e:
            logger.error(f"LLM 全面审核失败 | error={e}")
            return []

    @staticmethod
    def _truncate_for_llm(text: str, max_chars: int = 12000) -> str:
        """智能截断文本：保留开头 + 中间 + 结尾，确保关键信息不丢失"""
        if len(text) <= max_chars:
            return text

        head_size = max_chars * 2 // 3    # 前 2/3
        tail_size = max_chars // 6         # 后 1/6
        mid_size = max_chars - head_size - tail_size

        head = text[:head_size]
        mid_start = len(text) // 2 - mid_size // 2
        mid = text[mid_start:mid_start + mid_size]
        tail = text[-tail_size:]

        return f"{head}\n\n... [中间部分省略] ...\n\n{mid}\n\n... [中间部分省略] ...\n\n{tail}"


risk_engine = RiskEngine()
