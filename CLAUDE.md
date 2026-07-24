# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

企业级合同审批审查系统（Contract Approval Review System）。对接 OA 审批系统，自动拉取审批单和合同附件，通过 MinerU/PaddleOCR 解析文档、LLM 提取关键字段、规则引擎 + LLM 语义审查生成风险意见，最后回写审批评论区。

技术栈：**FastAPI (Python)** 后端 + **Vue 3 / Ant Design Vue 4 / TypeScript** 前端 + **MySQL + Redis + MinIO** 基础设施。

## Start / Develop Commands

### Backend (FastAPI)

```bash
cd backend
# Windows
.\start.ps1
# Linux/Mac
bash start.sh
# 或手动:
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API 文档: http://localhost:8000/docs
- 默认登录: `admin` / `admin123` 或 `reviewer` / `reviewer123`（见 `app/core/security.py` 的 `DEV_USERS`）
- 包管理用 `uv`（非 Poetry），Python >= 3.11
- 依赖锁文件: `uv.lock`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run mypy app/`
- 测试: `uv run pytest tests/ -v`

### Frontend (Vue 3 + Vite)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on port 5173
npm run build      # Production build
```

- Dev server 将 `/api/*` 代理到 `http://localhost:8001`（见 `vite.config.ts`）
- 登录后 token 存储于 localStorage key `token`
- UI 组件库: Ant Design Vue 4 (`ant-design-vue`)

### Infrastructure (Docker)

```bash
docker compose up -d    # 启动 MySQL + Redis + MinIO + Backend
```

- MySQL: `localhost:3306`, root/root123, database: `contract_review`
- Redis: `localhost:6379`
- MinIO: API `localhost:9000`, Console `localhost:9001`, minioadmin/minioadmin

## Architecture

### Backend (单体多模块)

入口: `app/main.py` → 注册路由 `app/api/v1/router.py`，使用 FastAPI lifespan 管理生命周期。

```
app/
├── api/v1/           # REST API 路由 (FastAPI APIRouter)
│   ├── router.py     # 总路由，prefix=/api/v1
│   ├── auth_router.py      # 登录/刷新/用户信息
│   ├── approval_router.py   # 审批单同步/查询
│   ├── contract_router.py   # 合同文档上传/解析/字段提取/下载
│   ├── risk_router.py      # 风险规则 CRUD + 审查结果/报告
│   ├── task_router.py      # 工作流任务查询
│   ├── dashboard_router.py  # 统计看板
│   ├── system_router.py     # 系统配置/日志
│   ├── webhook_router.py    # OA Webhook 回调
│   └── deps.py             # FastAPI 依赖注入 (get_db, verify_api_key, 各服务工厂)
├── services/         # 领域服务
│   ├── approval/     # 审批单拉取/同步
│   ├── contract/     # 合同文档管理
│   ├── parser/       # 文档解析 (MinerU/PaddleOCR/LLM字段提取)
│   ├── risk/         # 风险规则匹配 + 审查
│   └── workflow/     # 工作流任务管理
├── models/           # SQLAlchemy ORM 模型
├── repositories/     # Repository 模式封装数据访问
├── workflow/         # LangGraph 工作流引擎
│   ├── contract_review_workflow.py  # StateGraph 定义 (7节点 + 异常分支)
│   ├── workflow_nodes.py            # 各节点实现
│   ├── workflow_state.py            # WorkflowState 数据结构
│   └── checkpointer.py              # MySQL Checkpointer
├── infrastructure/   # MinIO/Redis 客户端封装
├── common/           # 雪花ID生成器、统一响应格式 (ApiResponse)
├── core/             # 配置(pydantic-settings)、JWT安全、数据库、异常处理、调度器
├── middleware/       # 请求ID追踪
└── mcp/              # MCP Server (将审查能力暴露为 MCP Tool)
```

### 两条认证路径，注意区分

| 路由组 | 认证依赖 | 说明 |
|--------|----------|------|
| `auth_router.py` | `get_current_user` → `HTTPBearer` → JWT | 登录/用户信息用 Bearer Token |
| 业务路由 (contracts/risks/approvals/…) | `verify_api_key` | **同时支持** X-API-Key Header 或 Bearer Token，优先 X-API-Key；`OA_API_KEY` 为空则跳过认证 |

### API 响应格式规范

所有后端 API 必须用 `ApiResponse` 包装返回，包含 `code`/`message`/`data` 字段：

```python
from app.common.response import ApiResponse
return ApiResponse.success(data={...}, message="操作成功")
```

前端 `request.ts` 的响应拦截器依赖 `code` 字段判断成功/失败。如果返回 dict 中**有 `message` 字段但无 `code` 字段**，会被拦截器误判为错误（表现为 `message.error('上传成功')`）。`contract_router.py` 在 v1.8 修复中已全部改用 `ApiResponse.success()`。

### 前端的两个响应拦截路径（成功拦截器）

`frontend/src/utils/request.ts` 响应成功拦截器逻辑：
1. `data.code === undefined && data.message === undefined` → 自动包装为 `{code:0, message:'success', data: rawData}`（兼容无包装的后端响应）
2. `data.code === 0` → 直接透传
3. `data.code === 401` → 清 token 跳转登录
4. 其他 → `message.error` + `Promise.reject`

## 工作流引擎 (LangGraph)

`contract_review_workflow.py` 定义审查流程 StateGraph，节点链：

```
fetch_approval → download_contract → parse_document → extract_fields → risk_review → comment_back → complete
```

每个节点有对应的 `on_*_error` 异常分支，按异常类型决定：自动重试（指数退避）/ 阻塞（BLOCKED，等待人工处理）/ 失败（FAILED）。Checkpoint 持久化到 MySQL 支持断点续跑。

## 前端路由结构

`frontend/src/router/index.ts` — 所有页面在 `/` 下的 DefaultLayout 中渲染：

- `/dashboard` — 统计看板
- `/approval-orders` — 审批单列表
- `/risk-results` — 风险审查结果
- `/risk-rules` — 风险规则管理
- `/workflow-tasks` — 工作流任务
- `/contract-docs` — 合同文档管理（上传/解析）
- `/system/config`、`/system/logs` — 系统管理

路由守卫 (`guards.ts`)：白名单 `['/login', '/404', '/500']`，无 token 跳转登录，有 token 调用 `fetchUserInfo()` 获取用户信息。

## 关键配置

- 后端: `backend/.env` — 数据库/Redis/MinIO/LLM/OA 配置
- 前端 env: `frontend/.env.development` — `VITE_API_BASE_URL=/api`, `VITE_USE_MOCK=false`
- 前端 mock: `frontend/vite.config.ts` 中的 `mockApiPlugin()` — 状态化 mock 数据，由 `USE_MOCK` 常量控制开关
- 前端 `request.ts` 中的旧 `buildMockData()` 是遗留代码，仅当 `VITE_USE_MOCK=true` 且后端不可达时触发

## 日志文件

后端日志使用 loguru，配置见 `app/core/logging_config.py`，日志目录为 `backend/logs/`（由 `LOG_DIR` 配置项控制，默认 `./logs`）：

| 文件 | 说明 |
|------|------|
| `backend/logs/app.{YYYY-MM-DD}.log` | 全量日志，按 10MB 轮转，保留 30 天 |
| `backend/logs/error.{YYYY-MM-DD}.log` | 仅 ERROR 级别，单独存储便于排查 |

- 日志格式由 `LOG_FORMAT` 控制（开发环境人类可读，生产环境 JSON）
- 异常处理器位于 `app/core/exception_handlers.py`，错误仅写入 loguru 文件，不写数据库 `t_system_log` 表

## 后端 API 接口全览

所有接口前缀 `/api/v1`，认证方式：`auth` 路由用 Bearer JWT，业务路由用 `X-API-Key` 或 Bearer Token（见 `deps.py` 的 `verify_api_key`）。

### 认证 (`/auth`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 用户登录，返回 JWT token |
| POST | `/auth/refresh` | 刷新 token |
| GET | `/auth/me` | 获取当前用户信息 |

### 审批单管理 (`/approvals`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/approvals` | 分页查询审批单列表 |
| GET | `/approvals/{approval_order_id}` | 查询审批单详情（含附件+评论） |
| POST | `/approvals/{approval_order_id}/sync` | 从 OA 同步审批单到本地 |

### 合同文档 (`/contracts`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/contracts/upload` | 上传合同文件（PDF/Word/图片），MD5 去重后存 MinIO |
| GET | `/contracts/` | 分页查询合同文档列表 |
| GET | `/contracts/{doc_id}` | 查询文档详情 |
| POST | `/contracts/{doc_id}/parse` | 触发文档解析（电子PDF→MinerU，扫描件→PaddleOCR） |
| GET | `/contracts/{doc_id}/parse-status` | 查询解析状态 |
| POST | `/contracts/{doc_id}/extract-fields` | 提取合同字段（调用 LLM） |
| POST | `/contracts/{doc_id}/review` | 直接从文档发起合同审查 |
| GET | `/contracts/{doc_id}/download-url` | 获取预签名下载 URL（1小时有效） |
| DELETE | `/contracts/{doc_id}` | 删除文档及 MinIO 文件 |

### 风险审查 (`/risks`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/risks/rules` | 创建风险规则 |
| GET | `/risks/rules` | 分页查询风险规则列表 |
| PUT | `/risks/rules/{rule_id}` | 更新风险规则 |
| DELETE | `/risks/rules/{rule_id}` | 删除风险规则 |
| POST | `/risks/rules/{rule_id}/toggle` | 启用/禁用风险规则 |
| GET | `/risks/results/{approval_order_id}` | 查询审批单的风险审查结果 |
| GET | `/risks/report/{approval_order_id}` | 生成风险审查报告 |
| POST | `/risks/results/{risk_id}/validate` | 人工确认/驳回风险项 |

### 工作流任务 (`/tasks`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks/review` | 创建合同审查任务（同步/异步） |
| POST | `/tasks/{task_id}/retry` | 重试失败/阻塞的任务 |
| GET | `/tasks/{task_id}` | 查询任务状态 |
| GET | `/tasks` | 分页查询任务列表 |

### 统计看板 (`/dashboard`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dashboard/stats` | 统计概览（审批单/合同/风险总数） |
| GET | `/dashboard/trend` | 审查趋势数据 |
| GET | `/dashboard/risk-distribution` | 风险等级分布 |

### 系统管理 (`/system`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/system/configs` | 获取所有系统配置 |
| PUT | `/system/configs/{config_key}` | 更新配置项 |
| GET | `/system/logs` | 分页查询操作日志 |

### Webhook 回调 (`/webhook`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/webhook/approval-status` | 接收 OA 审批状态变更通知（HMAC 签名校验） |
| POST | `/webhook/approval-status` | 同步审批单并触发审查 |
| GET | `/webhook/health` | Webhook 健康检查 |

## 项目核心业务流程

### 合同审查全链路（7 步）

```
触发方式：
  方式1：OA Webhook 回调 → 审批单创建时自动触发
  方式2：REST API POST /tasks/review → 手动触发
  方式3：前端 Dashboard 上传合同后 POST /contracts/{doc_id}/review
  方式4：MCP Client 调用 contract_review Tool

Step 1 — 拉取审批单
  ├── 根据 approval_order_id 调用 OA API 拉取审批单详情
  ├── 获取审批单状态、发起人、审批流程信息
  └── UPSERT 入库 t_approval_order

Step 2 — 下载合同附件
  ├── 遍历附件列表，校验文件类型（PDF/Word/图片）
  ├── 计算文件 MD5，检查是否已存在（去重）
  ├── 下载附件 → 上传到 MinIO
  └── 入库 t_contract_document

Step 3 — 文档解析
  ├── 电子 PDF → MinerU（magic-pdf CLI 子进程）
  ├── 扫描件/图片 → PaddleOCR
  └── 解析结果入库 t_contract_document.parse_text

Step 4 — 字段结构化提取
  ├── 解析文本传入 LLM（Qwen/DeepSeek）
  ├── 提取：合同编号、甲乙双方、金额、期限、付款条款、违约责任等
  └── 入库 t_contract_field

Step 5 — 规则风险审查
  ├── 加载启用的风险规则（字段匹配 + LLM 语义审查）
  ├── 逐条评估，生成风险项（高/中/低）
  └── 入库 t_risk_review_result

Step 6 — 审批评论回写
  ├── 格式化风险结果为评论内容（风险等级 + 高风险项 + 建议）
  ├── 调用 OA 评论 API 回写（comment_id 幂等）
  └── 入库 t_approval_comment

Step 7 — 任务完成
  ├── 更新任务状态为 SUCCESS
  └── 记录耗时
```

### 异常处理与重试

```
异常分类：
├── 可恢复（Recoverable）：网络超时、第三方服务不可用、LLM 限流
│   → 自动重试（指数退避：5s → 10s → 20s → ... 最大 300s，最多 3 次）
├── 不可恢复（NonRecoverable）：文件不存在、格式不支持、数据校验失败
│   → 任务标记 FAILED
└── 需人工介入（ManualIntervention）：OCR 置信度过低、字段提取不完整
    → 任务标记 BLOCKED，等待人工处理

超过最大重试次数 → 升级为 BLOCKED
```

### 数据库表关系

```
t_approval_order (审批单)          t_risk_rule (风险规则)
  │ 1:N                               │ 1:N
  ├── t_contract_document (合同文档)   └── t_risk_review_result (审查结果)
  │     1:1                              │
  │     └── t_contract_field (字段提取)   │
  │                                      │
  ├── t_approval_comment (评论记录)      │
  │                                      │
  └── t_workflow_task (工作流任务)       │
        1:N                              │
        └── t_task_retry_log (重试日志)  │

t_system_config (系统配置)    t_system_log (操作日志)
```

### 技术栈对照

| 设计文档 | 实际实现 |
|----------|----------|
| 依赖管理 Poetry | **uv**（pyproject.toml + uv.lock） |
| 后端端口 8000 | **8001**（前端代理到 8001） |
| 重试 5 次 / 间隔 1min~30min | **3 次 / 间隔 5s~300s** |
| 限流 Redis 滑动窗口 | **内存字典**（开发阶段） |
| 定时任务 3 个 | 调度器已启动但**未注册定时任务** |
| Word 转 PDF 解析 | **未实现**（仅识别文件类型） |
| 分布式锁 + Redis 缓存 | 基础设施就绪，**业务代码未接入** |