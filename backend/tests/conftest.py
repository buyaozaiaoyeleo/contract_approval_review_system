"""测试配置文件

提供 pytest fixtures: 数据库会话、HTTP 客户端、Mock 服务等。
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings

# ==================== 测试配置 ====================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """测试环境配置"""
    return Settings(
        APP_ENV="test",
        APP_DEBUG=True,
        DB_HOST="localhost",
        DB_PORT=3306,
        DB_USER="test",
        DB_PASSWORD="test",
        DB_NAME="contract_review_test",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        LLM_API_KEY="test-key",
        MINIO_ACCESS_KEY="test",
        MINIO_SECRET_KEY="test",
        OA_API_KEY=None,
    )


# ==================== 数据库 Fixtures ====================

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话（使用 SQLite 内存数据库）"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


# ==================== FastAPI 应用 Fixtures ====================

@pytest.fixture
def test_app() -> FastAPI:
    """创建测试 FastAPI 应用"""
    from app.main import create_app

    app = create_app()
    app.dependency_overrides = {}
    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """创建测试 HTTP 客户端"""
    return TestClient(test_app)


# ==================== Mock 工具 Fixtures ====================

@pytest.fixture
def mock_llm_response() -> dict:
    """Mock LLM 字段提取响应"""
    return {
        "contract_no": "HT-2024-0001",
        "party_a_info": {"name": "甲方公司", "address": "北京市朝阳区", "contact": "张三"},
        "party_b_info": {"name": "乙方公司", "address": "上海市浦东新区", "contact": "李四"},
        "amount": "500000元",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "payment_terms": "合同签订后30日内支付50%，验收后支付50%",
        "liability_clause": "违约方需支付合同总额20%的违约金",
        "confidentiality": "双方应对合同内容保密，保密期限5年",
        "dispute_resolution": "协商不成，向甲方所在地法院提起诉讼",
        "raw_json": "{}",
        "confidence": 0.92,
    }


@pytest.fixture
def mock_risk_review_response() -> dict:
    """Mock LLM 风险审查响应"""
    return {
        "has_risk": True,
        "risk_level": "MEDIUM",
        "risk_description": "付款条款存在风险：一次性支付比例过高",
        "suggestion": "建议修改为分阶段付款，降低首付比例至30%",
        "source_text": "合同签订后30日内支付50%...",
    }


@pytest.fixture
def mock_oa_response() -> dict:
    """Mock OA 审批单响应"""
    return {
        "approval_order_id": 12345,
        "title": "测试合同审批单",
        "status": "pending",
        "applicant": "张三",
        "department": "法务部",
        "created_at": "2024-01-01T00:00:00",
        "attachments": [
            {"file_name": "测试合同.pdf", "file_url": "http://oa.example.com/files/1.pdf"},
        ],
    }


# ==================== 测试数据工厂 ====================

@pytest.fixture
def sample_approval_data() -> dict:
    """测试审批单数据"""
    return {
        "approval_order_id": 12345,
        "title": "测试合同审批单",
        "status": "pending",
        "applicant": "张三",
        "department": "法务部",
    }


@pytest.fixture
def sample_contract_text() -> str:
    """测试合同文本"""
    return """
合同编号：HT-2024-0001

甲方：甲方科技有限公司
地址：北京市朝阳区科技园路1号
联系人：张三

乙方：乙方信息技术有限公司
地址：上海市浦东新区软件园2号
联系人：李四

合同金额：人民币伍拾万元整（¥500,000.00）

合同期限：2024年1月1日至2024年12月31日

付款条款：
1. 合同签订后30日内，甲方向乙方支付合同总额的50%
2. 项目验收合格后，甲方向乙方支付剩余50%

违约责任：
任何一方违反本合同约定，应向对方支付合同总额20%的违约金。

保密条款：
双方应对本合同内容及履行过程中知悉的对方商业秘密予以保密，保密期限为5年。

争议解决：
本合同履行过程中发生争议，双方协商解决；协商不成的，向甲方所在地人民法院提起诉讼。
"""


@pytest.fixture
def sample_risk_rules() -> list[dict]:
    """测试风险规则数据"""
    return [
        {
            "rule_code": "AMOUNT_LARGE",
            "rule_name": "大额合同审查",
            "rule_category": "amount",
            "rule_type": "field",
            "rule_config_json": '{"field":"amount","match_type":"range","min":1000000}',
            "risk_level": "HIGH",
            "priority": 10,
            "description": "合同金额超过100万需重点关注",
        },
        {
            "rule_code": "PAYMENT_TERMS",
            "rule_name": "付款条款审查",
            "rule_category": "clause",
            "rule_type": "llm",
            "rule_config_json": '{"field":"payment_terms","prompt":"检查付款条款是否公平合理"}',
            "risk_level": "MEDIUM",
            "priority": 5,
            "description": "检查付款条款的公平性",
        },
        {
            "rule_code": "MISSING_LIABILITY",
            "rule_name": "缺失违约责任",
            "rule_category": "clause",
            "rule_type": "field",
            "rule_config_json": '{"field":"liability_clause","match_type":"missing"}',
            "risk_level": "HIGH",
            "priority": 8,
            "description": "检查是否缺少违约责任条款",
        },
    ]
