"""应用配置管理 - 基于 pydantic-settings"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，所有配置项从 .env 文件和环境变量读取

    敏感字段使用 SecretStr 类型，避免日志/序列化中泄露。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",              # 忽略未定义的环境变量
    )

    # --- 应用配置 ---
    APP_NAME: str = Field(default="contract_approval_review_system", description="应用名称")
    APP_VERSION: str = Field(default="0.1.0", description="应用版本")
    APP_ENV: str = Field(default="development", description="运行环境: development / production")
    APP_DEBUG: bool = Field(default=True, description="调试模式")

    # --- 服务端口 ---
    SERVER_HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    SERVER_PORT: int = Field(default=8000, description="服务监听端口")

    # --- CORS 配置 ---
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="允许跨域请求的前端地址列表",
    )

    # --- 数据库配置 ---
    DB_HOST: str = Field(default="localhost", description="数据库主机")
    DB_PORT: int = Field(default=3306, description="数据库端口")
    DB_USER: str = Field(default="root", description="数据库用户名")
    DB_PASSWORD: SecretStr = Field(default=SecretStr(""), description="数据库密码")
    DB_NAME: str = Field(default="contract_review", description="数据库名称")
    DB_POOL_SIZE: int = Field(default=20, description="连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=40, description="最大溢出连接数")
    DB_ECHO: bool = Field(default=False, description="是否打印SQL日志")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    # --- Redis 配置 ---
    REDIS_HOST: str = Field(default="localhost", description="Redis 主机")
    REDIS_PORT: int = Field(default=6379, description="Redis 端口")
    REDIS_PASSWORD: str | None = Field(default=None, description="Redis 密码")
    REDIS_DB: int = Field(default=0, description="Redis 数据库编号")
    REDIS_PREFIX: str = Field(default="contract_review:", description="Redis Key 前缀")

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- MinIO 配置 ---
    MINIO_ENDPOINT: str = Field(default="localhost:9000", description="MinIO 服务地址")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", description="MinIO 访问密钥")
    MINIO_SECRET_KEY: SecretStr = Field(default=SecretStr("minioadmin"), description="MinIO 密钥")
    MINIO_BUCKET: str = Field(default="contract-documents", description="默认存储桶")
    MINIO_SECURE: bool = Field(default=False, description="是否使用 HTTPS")

    # --- OA 系统配置 ---
    OA_BASE_URL: str = Field(default="http://localhost:8080", description="OA 系统基础地址")
    OA_API_KEY: str | None = Field(default=None, description="OA 系统 API Key")
    OA_TIMEOUT: int = Field(default=30, description="OA 请求超时时间(秒)")

    # --- LLM 配置 ---
    LLM_PROVIDER: str = Field(default="qwen", description="LLM 提供商: qwen / deepseek")
    LLM_API_KEY: SecretStr = Field(default=SecretStr(""), description="LLM API Key")
    LLM_BASE_URL: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", description="LLM API 地址")
    LLM_MODEL_NAME: str = Field(default="qwen-plus", description="模型名称")
    LLM_TEMPERATURE: float = Field(default=0.1, description="生成温度")
    LLM_MAX_TOKENS: int = Field(default=4096, description="最大 Token 数")

    # --- 日志配置 ---
    LOG_LEVEL: str = Field(default="DEBUG", description="日志级别")
    LOG_DIR: str = Field(default="./logs", description="日志文件目录")
    LOG_FORMAT: str = Field(default="json", description="日志格式: json / text")
    LOG_ROTATION: str = Field(default="10 MB", description="日志轮转大小")
    LOG_RETENTION: str = Field(default="30 days", description="日志保留时间")

    # --- 雪花 ID 配置 ---
    SNOWFLAKE_WORKER_ID: int = Field(default=1, ge=0, le=31, description="雪花算法 Worker ID")
    SNOWFLAKE_DATACENTER_ID: int = Field(default=1, ge=0, le=31, description="雪花算法数据中心 ID")

    # --- 工作流配置 ---
    WORKFLOW_MAX_RETRY: int = Field(default=5, description="工作流最大重试次数")
    WORKFLOW_RETRY_BASE_DELAY: int = Field(default=60, description="重试基础延迟(秒)")
    WORKFLOW_RETRY_MAX_DELAY: int = Field(default=1800, description="重试最大延迟(秒)")
    WORKFLOW_TASK_TIMEOUT: int = Field(default=600, description="任务超时时间(秒)")

    # --- 安全配置 ---
    SECRET_KEY: SecretStr = Field(default=SecretStr("change_me"), description="JWT 签名密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 算法")
    JWT_EXPIRE_MINUTES: int = Field(default=1440, description="JWT 过期时间(分钟)")

    # --- MCP 配置 ---
    MCP_SERVER_NAME: str = Field(default="contract-review-mcp", description="MCP 服务名称")
    MCP_SERVER_VERSION: str = Field(default="0.1.0", description="MCP 服务版本")
    MCP_TRANSPORT: str = Field(default="sse", description="MCP 传输协议: sse / stdio")

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
