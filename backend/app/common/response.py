"""统一响应格式定义"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str = Field(default="", description="请求追踪 ID")
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now().timestamp() * 1000),
        description="响应时间戳(毫秒)",
    )

    @classmethod
    def success(
        cls,
        data: T = None,
        message: str = "success",
        trace_id: str = "",
    ) -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data, trace_id=trace_id)

    @classmethod
    def error(
        cls,
        code: int = 50000,
        message: str = "服务内部错误",
        trace_id: str = "",
        data: Any = None,
    ) -> "ApiResponse":
        return cls(code=code, message=message, data=data, trace_id=trace_id)


class PageInfo(BaseModel):
    """分页信息"""

    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    total: int = Field(default=0, ge=0, description="总记录数")
    total_pages: int = Field(default=0, ge=0, description="总页数")

    @classmethod
    def of(cls, page: int, page_size: int, total: int) -> "PageInfo":
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(page=page, page_size=page_size, total=total, total_pages=total_pages)


class PageResult(BaseModel, Generic[T]):
    """分页查询结果"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    page_info: PageInfo = Field(default_factory=PageInfo, description="分页信息")

    @classmethod
    def of(cls, items: list[T], page: int, page_size: int, total: int) -> "PageResult[T]":
        return cls(items=items, page_info=PageInfo.of(page, page_size, total))
