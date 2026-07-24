"""MCP 传输层

支持 SSE 和 stdio 两种传输方式：
- SSE: 适合 Web 部署，通过 HTTP 传输
- stdio: 适合本地 CLI 工具调用

FastMCP 内置了 run_sse_async / run_stdio_async 方法，直接调用即可。
"""

import asyncio

from loguru import logger

from app.core.config import settings
from app.mcp.mcp_server import mcp

# ==================== SSE 传输层 ====================

async def run_sse_server(host: str = "0.0.0.0", port: int = 8001):
    """启动 SSE 传输服务器

    使用 FastMCP 内置的 run_sse_async 启动 HTTP SSE 服务。
    客户端可通过 http://{host}:{port}/ 访问 MCP 服务。
    """
    logger.info(f"MCP SSE Server 启动 | host={host} | port={port} | version={settings.APP_VERSION}")
    await mcp.run_sse_async(host=host, port=port)


# ==================== stdio 传输层 ====================

async def run_stdio_server():
    """启动 stdio 传输服务器（用于本地 CLI 工具调用）

    适用场景：Cursor / Claude Desktop 等 MCP 客户端通过 stdio 连接。
    """
    logger.info("MCP stdio Server 启动")
    await mcp.run_stdio_async()


# ==================== 统一启动入口 ====================

def start_mcp_server(transport: str = "sse", host: str = "0.0.0.0", port: int = 8001):
    """启动 MCP 服务器

    Args:
        transport: 传输方式 - "sse" 或 "stdio"
        host: SSE 监听地址
        port: SSE 监听端口
    """
    if transport == "stdio":
        asyncio.run(run_stdio_server())
    else:
        asyncio.run(run_sse_server(host, port))
