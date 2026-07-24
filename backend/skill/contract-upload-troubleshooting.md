# 合同上传功能排障 Skill

> 从实战排障中提炼，覆盖 CORS / 上传 500 / MinIO 连通性 等高频问题。

---

## 1. CORS 被浏览器拦截

**现象**：浏览器控制台报 `Access-Control-Allow-Origin` 缺失。

**根因链路**：
```
前端请求 /api/v1/contracts（无尾部斜杠）
  → Vite proxy 转发到 localhost:8001
  → FastAPI 路由定义为 /contracts/（有尾部斜杠）
  → 返回 307 重定向到 /contracts/
  → 浏览器跟随重定向直接访问 localhost:8001（绕过 Vite proxy）
  → 后端无 CORS 中间件 → 浏览器拦截
```

**修复**（`backend/app/main.py`）：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**配置**（`backend/app/core/config.py`）：
```python
CORS_ORIGINS: list[str] = Field(
    default=["http://localhost:5173", "http://localhost:3000"],
)
```

**前端侧**：确保 API 调用 URL 与后端路由斜杠一致。如后端路由是 `/contracts/`，前端应请求 `/v1/contracts/` 而非 `/v1/contracts`。

---

## 2. 上传报 500（数据库主键缺失）

**现象**：`POST /api/v1/contracts/upload` → 500 Internal Server Error。

**日志关键字**：`IntegrityError` 或 `NOT NULL constraint` 在 `id` 列。

**根因**：`ContractDocument` 使用了 `SnowflakePKMixin`，主键 `id` 是 `BigInteger, primary_key=True, autoincrement=False`——数据库不会自动生成 ID，必须由应用手动调用 `generate_id()` 分配。

**错误写法**（`contract_router.py`）：
```python
doc = ContractDocument(
    doc_id=doc_id,
    approval_order_id=...,
    ...
)
# ❌ 漏了 id=generate_id()
```

**正确写法**：
```python
doc = ContractDocument(
    id=generate_id(),      # ← 必须手动分配雪花 ID
    doc_id=doc_id,
    approval_order_id=...,
    ...
)
```

**排查方法**：看 `backend/logs/error.{date}.log`，搜索 `contract_router.py` 附近的异常。

---

## 3. MinIO 连通性与端口

### 3.1 MinIO 两个端口不能混用

| 端口 | 用途 | 协议 |
|------|------|------|
| **9000** | S3 API（SDK 调用） | S3 |
| **9001** | Web Console（浏览器） | HTTP |

`minio-py` SDK 只能通过 **API 端口（9000）** 通信。如果 `MINIO_ENDPOINT` 配成 9001 端口：
- `minio_client.connect()` 不会报错（Minio 构造函数是 lazy 的，不实际连接）
- `ensure_bucket()` / `put_object()` 会报：`S3 API Requests must be made to API port.`

### 3.2 测试连通性

```bash
cd backend
uv run python -c "
from minio import Minio
c = Minio('IP:9000', 'minioadmin', 'minioadmin', secure=False)
print([b.name for b in c.list_buckets()])
"
```

成功输出形如 `['a-bucket', 'contract-documents']`。

### 3.3 NoSuchBucket 错误

**现象**：`S3Error: NoSuchBucket, bucket_name: contract-documents`。

**原因**：启动时 `ensure_bucket()` 失败被静默捕获（`MinIO 连接失败(非致命)`），bucket 未创建。

**手动创建**：
```python
c = Minio('IP:9000', 'minioadmin', 'minioadmin', secure=False)
c.make_bucket('contract-documents')
```

**排查**：看 `backend/logs/app.{date}.log` 搜索 `MinIO 连接失败(非致命)`，确认 endpoint 是否正确。

---

## 4. MinIO 客户端 async 陷阱

**问题**：`minio-py` 库是**纯同步**的，所有方法（`put_object`、`get_object` 等）都会阻塞线程。

**错误写法**（旧版 `minio_client.py`）：
```python
async def upload(self, ...):
    self.client.put_object(...)  # ❌ 在 async 函数中调用同步阻塞 IO
```

**正确写法**——使用 `asyncio.to_thread()` 将同步调用丢进线程池：
```python
import asyncio

async def upload(self, ...):
    def _upload():
        self.client.put_object(...)
    await asyncio.to_thread(_upload)
```

所有涉及网络 IO 的 MinIO 方法（upload / download / delete / exists）都应按此模式改写。

---

## 5. 通用排障流程

1. **看后端日志**：`backend/logs/error.{date}.log` 找 `general_exception_handler`
2. **看启动日志**：`backend/logs/app.{date}.log` 搜索 `WARNING` 看哪些初始化被静默跳过
3. **测 MinIO**：用上面的一行 Python 脚本验证连通性
4. **确认 `.env` 配置**：端口、账号密码、bucket 名称是否与 MinIO 实际一致
