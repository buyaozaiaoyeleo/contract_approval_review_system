"""API 中间件

提供请求日志、限流、CORS 等中间件。
"""

import time
from collections import defaultdict

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

# ==================== 请求日志中间件 ====================

class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的耗时和状态码"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path} "
            f"| status={response.status_code} "
            f"| elapsed={elapsed_ms:.2f}ms"
        )

        return response


# ==================== 简单限流中间件 ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于内存的简单限流（生产环境建议使用 Redis 滑动窗口）

    默认限制：100 次/分钟 每 IP
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._cache: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = self._get_client_ip(request)
        now = time.time()

        # 清理过期记录
        self._cache[client_ip] = [
            t for t in self._cache[client_ip]
            if now - t < self.window_seconds
        ]

        if len(self._cache[client_ip]) >= self.max_requests:
            from fastapi.responses import JSONResponse

            logger.warning(f"限流触发 | ip={client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
            )

        self._cache[client_ip].append(now)
        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """获取客户端 IP（考虑代理）"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ==================== CORS 中间件 ====================

def create_cors_middleware():
    """创建 CORS 中间件配置"""
    from app.core.config import settings

    return {
        "middleware_class": CORSMiddleware,
        "allow_origins": ["*"] if settings.APP_DEBUG else [],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
