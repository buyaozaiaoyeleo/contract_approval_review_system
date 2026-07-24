"""JWT 令牌生成与验证

提供：
- create_access_token: 生成访问令牌
- verify_token: 验证令牌有效性
- get_token_payload: 从令牌中提取载荷
- authenticate_user: 用户凭据验证
"""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def _hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与 bcrypt 哈希值是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ==================== 开发环境默认账号 ====================

DEV_USERS = {
    "admin": {
        "username": "admin",
        "password_hash": _hash_password("admin123"),
        "display_name": "系统管理员",
        "roles": ["admin"],
        "permissions": ["*"],
    },
    "reviewer": {
        "username": "reviewer",
        "password_hash": _hash_password("reviewer123"),
        "display_name": "审查员",
        "roles": ["reviewer"],
        "permissions": ["task:read", "task:write", "risk:read", "risk:write"],
    },
}


# ==================== JWT 令牌操作 ====================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT 访问令牌

    Args:
        data: 要编码到令牌中的载荷数据（如 username）
        expires_delta: 过期时间间隔，默认使用配置中的 JWT_EXPIRE_MINUTES

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> dict | None:
    """验证 JWT 令牌并返回载荷

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的载荷字典，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def get_token_payload(token: str) -> dict | None:
    """从令牌中提取载荷（不验证过期）

    Args:
        token: JWT 令牌字符串

    Returns:
        载荷字典，解析失败返回 None
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None


# ==================== 用户认证 ====================

def authenticate_user(username: str, password: str) -> dict | None:
    """验证用户凭据

    开发环境使用内存中的 DEV_USERS 字典，
    生产环境应替换为数据库查询。

    Args:
        username: 用户名
        password: 明文密码

    Returns:
        用户信息字典，认证失败返回 None
    """
    user = DEV_USERS.get(username)
    if not user:
        return None
    if not _verify_password(password, user["password_hash"]):
        return None
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "roles": user["roles"],
        "permissions": user["permissions"],
    }
