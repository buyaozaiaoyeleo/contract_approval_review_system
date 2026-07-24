"""MCP Server 初始化

使用 FastMCP 创建 MCP 服务器，提供合同审查工具。
支持 SSE 和 stdio 两种传输方式。
"""

from mcp.server.fastmcp import FastMCP

from app.core.config import settings

# ==================== MCP Server 实例 ====================

mcp = FastMCP(
    name="contract_review",
    instructions="合同审批审查系统 - 提供合同自动化审查、风险分析、审批管理工具。"
    f"版本: {settings.APP_VERSION}",
)


# ==================== 资源定义 ====================

@mcp.resource("config://app")
async def get_app_config() -> str:
    """获取应用配置信息"""
    return f"""
应用名称: {settings.APP_NAME}
版本: {settings.APP_VERSION}
环境: {settings.APP_ENV}
LLM 模型: {settings.LLM_MODEL_NAME}
""".strip()


# ==================== 获取服务器实例 ====================

def get_mcp_server() -> FastMCP:
    """获取 MCP Server 实例"""
    return mcp
