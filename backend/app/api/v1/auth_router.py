"""认证 API 路由

提供登录、令牌刷新、当前用户信息等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.common.response import ApiResponse
from app.core.security import (
    authenticate_user,
    create_access_token,
    verify_token,
)

router = APIRouter(prefix="/auth")

# HTTP Bearer 认证方案
security_scheme = HTTPBearer(auto_error=False)


# ==================== 请求/响应模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌（当前与 access_token 相同）")
    expires_in: int = Field(..., description="过期时间(秒)")


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")


class UserInfoResponse(BaseModel):
    """当前用户信息"""
    id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    display_name: str = Field(..., description="显示名称")
    avatar: str | None = Field(default=None, description="头像 URL")
    roles: list[str] = Field(default_factory=list, description="角色列表")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


# ==================== 认证依赖 ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    """从 Bearer Token 中获取当前用户信息（依赖注入）

    验证失败时返回 401。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )

    from app.core.security import DEV_USERS

    username = payload.get("sub")
    if not username or username not in DEV_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    user = DEV_USERS[username]
    return {
        "id": username,
        "username": user["username"],
        "display_name": user["display_name"],
        "roles": user["roles"],
        "permissions": user["permissions"],
    }


# ==================== API 端点 ====================

@router.post("/login", summary="用户登录")
async def login(request: LoginRequest):
    """用户登录接口

    验证用户名和密码，返回 JWT 访问令牌。
    默认账号：admin / admin123
    """
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 生成访问令牌（24小时有效）
    token_data = {"sub": user["username"], "roles": user["roles"]}
    access_token = create_access_token(token_data)

    login_result = LoginResponse(
        access_token=access_token,
        refresh_token=access_token,
        expires_in=86400,  # 24小时
    )
    return ApiResponse.success(data=login_result, message="登录成功")


@router.post("/refresh", summary="刷新令牌")
async def refresh_token(request: RefreshRequest):
    """刷新访问令牌

    验证刷新令牌有效性后，颁发新的访问令牌。
    """
    payload = verify_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )

    username = payload.get("sub")
    roles = payload.get("roles", [])

    access_token = create_access_token({"sub": username, "roles": roles})
    login_result = LoginResponse(
        access_token=access_token,
        refresh_token=access_token,
        expires_in=86400,
    )
    return ApiResponse.success(data=login_result)


@router.get("/me", summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户的信息

    需要 Bearer Token 认证。
    """
    user_info = UserInfoResponse(
        id=current_user["username"],
        username=current_user["username"],
        display_name=current_user["display_name"],
        avatar=None,
        roles=current_user["roles"],
        permissions=current_user["permissions"],
    )
    return ApiResponse.success(data=user_info)
