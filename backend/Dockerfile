# ============================================================
# 合同审批审查系统 - Dockerfile
# ============================================================

FROM python:3.11-slim

LABEL maintainer="dev"
LABEL description="合同审批审查系统后端服务"

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT="/usr/local" \
    UV_LINK_MODE=copy

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock* ./

# 安装依赖（仅生产依赖，不安装 dev 组）
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码
COPY . .

# 复制启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]