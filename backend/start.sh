#!/bin/bash
# ============================================================
# 合同审批审查系统 - 后端启动脚本 (Linux/Mac)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  合同审批审查系统 - 后端服务启动"
echo "=============================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "[警告] .env 文件不存在，将使用 .env.example 作为默认配置"
    cp .env.example .env
fi

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo "[错误] 未找到 uv，请先安装: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# 安装依赖
echo "[1/3] 同步项目依赖..."
uv sync

# 创建日志目录
mkdir -p logs

# 启动服务
echo "[2/3] 启动 FastAPI 服务..."
echo "[3/3] 服务地址: http://${SERVER_HOST:-0.0.0.0}:${SERVER_PORT:-8000}"
echo "  - API 文档: http://${SERVER_HOST:-0.0.0.0}:${SERVER_PORT:-8000}/docs"
echo "  - 健康检查: http://${SERVER_HOST:-0.0.0.0}:${SERVER_PORT:-8000}/api/v1/health"
echo "=============================================="

uv run uvicorn app.main:app \
    --host "${SERVER_HOST:-0.0.0.0}" \
    --port "${SERVER_PORT:-8000}" \
    --reload \
    --log-level info