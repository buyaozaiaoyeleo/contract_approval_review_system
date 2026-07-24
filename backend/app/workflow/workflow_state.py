"""LangGraph 工作流状态定义

使用 TypedDict 定义工作流中节点间传递的状态，LangGraph 基于此构建状态图。
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    """合同审查工作流状态

    LangGraph 状态图的核心数据结构，每个节点读取/写入此状态。
    使用 total=False 使所有字段可选，节点只设置需要的字段。
    """

    # ==================== 任务标识 ====================
    task_id: str
    approval_order_id: int
    workflow_name: str

    # ==================== 审批单信息 ====================
    approval_data: dict | None           # OA 返回的审批单原始数据
    approval_exists: bool                    # 审批单是否存在
    approval_status: str                     # 审批单当前状态

    # ==================== 合同文档信息 ====================
    doc_id: str | None                    # 合同文档业务 ID
    file_md5: str | None                  # 文件 MD5 值（去重用）
    minio_path: str | None                # MinIO 存储路径
    doc_exists: bool                         # 文档是否已存在（去重命中）

    # ==================== 文档解析结果 ====================
    parse_text: str | None               # 解析后的全文文本
    parse_status: str                       # 解析状态: pending/parsing/parsed/failed
    page_count: int                         # 文档页数
    is_scanned: bool                         # 是否扫描件

    # ==================== 字段提取结果 ====================
    contract_no: str | None              # 合同编号
    party_a_info: dict | None            # 甲方信息
    party_b_info: dict | None            # 乙方信息
    amount: str | None                   # 合同金额
    start_date: str | None               # 开始日期
    end_date: str | None                 # 结束日期
    payment_terms: str | None            # 付款条款
    liability_clause: str | None         # 违约责任
    extract_confidence: float               # 提取置信度
    field_extracted: bool                    # 字段是否已提取

    # ==================== 风险审查结果 ====================
    risk_results: list[dict]                # 风险结果列表
    risk_score: dict                        # 综合评分
    risk_count: int                         # 风险项总数
    has_risks: bool                         # 是否有风险

    # ==================== 评论回写 ====================
    comment_content: str | None          # 评论内容
    comment_written: bool                   # 是否已回写

    # ==================== 任务控制 ====================
    current_node: str                       # 当前执行节点
    error_message: str | None            # 错误信息
    error_type: str | None               # 错误类型
    retry_count: int                        # 已重试次数
    max_retries: int                        # 最大重试次数
    is_blocked: bool                        # 是否阻塞
    block_reason: str | None             # 阻塞原因
    node_statuses: dict                     # 各节点执行状态 {"pull_approval": "completed", "parse_document": "failed"}
    failed_node: str | None              # 失败节点名称

    # ==================== 消息（用于 Human-in-the-loop） ====================
    messages: Annotated[list, add_messages]  # 人机交互消息

    # ==================== 时间戳 ====================
    started_at: str | None               # 开始时间
    completed_at: str | None             # 完成时间
    duration_ms: int | None              # 执行耗时(毫秒)
