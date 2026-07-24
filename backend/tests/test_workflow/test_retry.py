"""重试机制单元测试"""


from app.workflow.contract_review_workflow import RetryConfig


class TestRetryConfig:
    """重试配置测试"""

    def test_base_delay(self):
        """测试基础延迟"""
        assert RetryConfig.BASE_DELAY_SECONDS == 5

    def test_max_retries(self):
        """测试最大重试次数"""
        assert RetryConfig.MAX_RETRIES == 3

    def test_exponential_backoff(self):
        """测试指数退避计算"""
        assert RetryConfig.get_delay(0) == 5    # 5 * 2^0 = 5
        assert RetryConfig.get_delay(1) == 10   # 5 * 2^1 = 10
        assert RetryConfig.get_delay(2) == 20   # 5 * 2^2 = 20
        assert RetryConfig.get_delay(3) == 40   # 5 * 2^3 = 40

    def test_max_delay_cap(self):
        """测试延迟上限"""
        delay = RetryConfig.get_delay(10)  # 5 * 2^10 = 5120 > 300
        assert delay == 300

    def test_retryable_errors(self):
        """测试可重试错误判断"""
        assert RetryConfig.is_retryable("ConnectionError") is True
        assert RetryConfig.is_retryable("TimeoutError") is True
        assert RetryConfig.is_retryable("HTTPError") is True
        assert RetryConfig.is_retryable("RequestException") is True
        assert RetryConfig.is_retryable("TemporaryError") is True

    def test_non_retryable_errors(self):
        """测试不可重试错误判断"""
        assert RetryConfig.is_retryable("ValueError") is False
        assert RetryConfig.is_retryable("NoAttachmentError") is False
        assert RetryConfig.is_retryable("UnknownError") is False

    def test_blockable_errors(self):
        """测试阻塞错误判断"""
        assert RetryConfig.should_block("NoAttachmentError") is True
        assert RetryConfig.should_block("MissingDocIdError") is True
        assert RetryConfig.should_block("MissingParseTextError") is True
        assert RetryConfig.should_block("ValueError") is True

    def test_non_blockable_errors(self):
        """测试非阻塞错误判断"""
        assert RetryConfig.should_block("ConnectionError") is False
        assert RetryConfig.should_block("TimeoutError") is False


class TestWorkflowState:
    """工作流状态测试"""

    def test_state_initialization(self):
        """测试状态初始化"""
        from app.workflow.workflow_state import WorkflowState

        state: WorkflowState = {
            "task_id": "TASK_TEST",
            "approval_order_id": 12345,
            "workflow_name": "contract_review",
            "approval_exists": False,
            "doc_exists": False,
            "parse_status": "pending",
            "page_count": 0,
            "is_scanned": False,
            "field_extracted": False,
            "extract_confidence": 0.0,
            "risk_results": [],
            "risk_score": {},
            "risk_count": 0,
            "has_risks": False,
            "comment_written": False,
            "current_node": "",
            "retry_count": 0,
            "max_retries": 3,
            "is_blocked": False,
            "messages": [],
        }

        assert state["task_id"] == "TASK_TEST"
        assert state["retry_count"] == 0
        assert state["max_retries"] == 3
        assert state["is_blocked"] is False

    def test_state_fields_optional(self):
        """测试状态字段可选性"""
        from app.workflow.workflow_state import WorkflowState

        # 最小状态
        state: WorkflowState = {
            "task_id": "TASK_MIN",
            "approval_order_id": 1,
            "messages": [],
        }

        assert state.get("parse_text") is None
        assert state.get("error_message") is None
