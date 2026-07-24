"""统一异常体系定义"""

from typing import Any


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str = "服务内部错误",
        code: int = 50000,
        status_code: int = 500,
        detail: Any | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


# ============================================================
# 客户端异常 (4xx)
# ============================================================

class BadRequestException(AppException):
    """请求参数错误"""

    def __init__(self, message: str = "请求参数错误", detail: Any | None = None):
        super().__init__(message=message, code=40000, status_code=400, detail=detail)


class UnauthorizedException(AppException):
    """未认证"""

    def __init__(self, message: str = "未认证或认证已过期", detail: Any | None = None):
        super().__init__(message=message, code=40100, status_code=401, detail=detail)


class ForbiddenException(AppException):
    """无权限"""

    def __init__(self, message: str = "无访问权限", detail: Any | None = None):
        super().__init__(message=message, code=40300, status_code=403, detail=detail)


class NotFoundException(AppException):
    """资源不存在"""

    def __init__(self, message: str = "请求的资源不存在", detail: Any | None = None):
        super().__init__(message=message, code=40400, status_code=404, detail=detail)


class ConflictException(AppException):
    """资源冲突"""

    def __init__(self, message: str = "资源冲突", detail: Any | None = None):
        super().__init__(message=message, code=40900, status_code=409, detail=detail)


class ValidationException(AppException):
    """数据校验失败"""

    def __init__(self, message: str = "数据校验失败", detail: Any | None = None):
        super().__init__(message=message, code=42200, status_code=422, detail=detail)


# ============================================================
# 业务异常 (5xx 业务码)
# ============================================================

class ApprovalException(AppException):
    """审批单服务异常"""

    def __init__(self, message: str = "审批单服务异常", detail: Any | None = None):
        super().__init__(message=message, code=50001, status_code=500, detail=detail)


class ApprovalNotFoundException(NotFoundException):
    """审批单不存在"""

    def __init__(self, approval_id: str):
        super().__init__(message=f"审批单不存在: {approval_id}", detail={"approval_id": approval_id})


class ApprovalFetchException(AppException):
    """审批单拉取失败"""

    def __init__(self, message: str = "审批单拉取失败", detail: Any | None = None):
        super().__init__(message=message, code=50002, status_code=500, detail=detail)


class ApprovalCommentException(AppException):
    """审批评论回写失败"""

    def __init__(self, message: str = "审批评论回写失败", detail: Any | None = None):
        super().__init__(message=message, code=50003, status_code=500, detail=detail)


class ContractDocumentException(AppException):
    """合同文档服务异常"""

    def __init__(self, message: str = "合同文档服务异常", detail: Any | None = None):
        super().__init__(message=message, code=50010, status_code=500, detail=detail)


class DocumentDownloadException(AppException):
    """文档下载失败"""

    def __init__(self, message: str = "文档下载失败", detail: Any | None = None):
        super().__init__(message=message, code=50011, status_code=500, detail=detail)


class DocumentParseException(AppException):
    """文档解析失败"""

    def __init__(self, message: str = "文档解析失败", detail: Any | None = None):
        super().__init__(message=message, code=50012, status_code=500, detail=detail)


class OCRException(AppException):
    """OCR 识别失败"""

    def __init__(self, message: str = "OCR 识别失败", detail: Any | None = None):
        super().__init__(message=message, code=50013, status_code=500, detail=detail)


class FieldExtractionException(AppException):
    """字段提取失败"""

    def __init__(self, message: str = "字段提取失败", detail: Any | None = None):
        super().__init__(message=message, code=50020, status_code=500, detail=detail)


class RiskReviewException(AppException):
    """风险审查服务异常"""

    def __init__(self, message: str = "风险审查服务异常", detail: Any | None = None):
        super().__init__(message=message, code=50030, status_code=500, detail=detail)


class WorkflowException(AppException):
    """工作流异常"""

    def __init__(self, message: str = "工作流执行异常", detail: Any | None = None):
        super().__init__(message=message, code=50040, status_code=500, detail=detail)


class TaskBlockedException(AppException):
    """任务阻塞异常"""

    def __init__(self, message: str = "任务已阻塞，等待人工处理", detail: Any | None = None):
        super().__init__(message=message, code=50041, status_code=500, detail=detail)


class TaskRetryExhaustedException(AppException):
    """任务重试次数耗尽"""

    def __init__(self, message: str = "任务重试次数已耗尽", detail: Any | None = None):
        super().__init__(message=message, code=50042, status_code=500, detail=detail)


class LLMException(AppException):
    """LLM 调用异常"""

    def __init__(self, message: str = "大模型调用异常", detail: Any | None = None):
        super().__init__(message=message, code=50050, status_code=500, detail=detail)


class MinIOException(AppException):
    """MinIO 存储异常"""

    def __init__(self, message: str = "文件存储服务异常", detail: Any | None = None):
        super().__init__(message=message, code=50060, status_code=500, detail=detail)


class DatabaseException(AppException):
    """数据库异常"""

    def __init__(self, message: str = "数据库服务异常", detail: Any | None = None):
        super().__init__(message=message, code=50070, status_code=500, detail=detail)


class ExternalServiceException(AppException):
    """外部服务调用异常"""

    def __init__(self, message: str = "外部服务调用异常", detail: Any | None = None):
        super().__init__(message=message, code=50080, status_code=500, detail=detail)
