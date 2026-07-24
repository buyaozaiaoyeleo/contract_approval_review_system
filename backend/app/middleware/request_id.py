"""请求追踪 ID 中间件"""


from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.common.snowflake import generate_id_str


class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求追踪 ID 中间件

    为每个请求生成唯一 trace_id，注入到请求上下文和响应头中
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 优先使用客户端传入的 X-Request-ID，否则生成
        trace_id = request.headers.get("X-Request-ID", generate_id_str())

        # 注入到 request.state 供后续使用
        request.state.trace_id = trace_id

        # 处理请求
        response = await call_next(request)

        # 响应头中返回 trace_id
        response.headers["X-Request-ID"] = trace_id

        return response
