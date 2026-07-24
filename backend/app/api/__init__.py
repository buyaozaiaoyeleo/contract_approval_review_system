"""API 模块导出"""

from app.api.v1.router import router as v1_router

__all__ = ["v1_router"]
