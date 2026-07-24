"""MCP 工具集成模块导出"""

# 导入工具注册模块（触发 @mcp.tool 装饰器注册）
import app.mcp.mcp_tools  # noqa: F401
from app.mcp.mcp_server import get_mcp_server, mcp
from app.mcp.transport import start_mcp_server

__all__ = [
    "mcp",
    "get_mcp_server",
    "start_mcp_server",
]
