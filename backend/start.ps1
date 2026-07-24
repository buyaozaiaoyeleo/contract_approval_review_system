# ============================================================
# 合同审批审查系统 - 后端启动脚本 (Windows PowerShell)
# ============================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  合同审批审查系统 - 后端服务启动" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "[警告] .env 文件不存在，将使用 .env.example 作为默认配置" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 检查 uv
$uvExists = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvExists) {
    Write-Host "[错误] 未找到 uv，请先安装: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "[1/3] 同步项目依赖..." -ForegroundColor Green
uv sync

# 创建日志目录
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# 读取环境变量
$envFile = Get-Content .env | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' }
$envVars = @{}
foreach ($line in $envFile) {
    if ($line -match '^\s*([^=]+)\s*=\s*(.*)$') {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$ServerHost = if ($envVars.ContainsKey("SERVER_HOST")) { $envVars["SERVER_HOST"] } else { "0.0.0.0" }
$ServerPort = if ($envVars.ContainsKey("SERVER_PORT")) { $envVars["SERVER_PORT"] } else { "8000" }

# 启动服务
Write-Host "[2/3] 启动 FastAPI 服务..." -ForegroundColor Green
Write-Host "[3/3] 服务地址: http://${ServerHost}:${ServerPort}" -ForegroundColor Green
Write-Host "  - API 文档: http://${ServerHost}:${ServerPort}/docs" -ForegroundColor Green
Write-Host "  - 健康检查: http://${ServerHost}:${ServerPort}/api/v1/health" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

uv run uvicorn app.main:app --host $ServerHost --port $ServerPort --reload --log-level info