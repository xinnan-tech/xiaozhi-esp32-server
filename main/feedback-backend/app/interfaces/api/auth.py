"""JWT 认证模块 - 后台管理登录"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import AdminUserModel, StoreModel
from app.shared.config import settings

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token
security = HTTPBearer()

ROLE_SUPER_ADMIN = "super_admin"
ROLE_STORE_MANAGER = "store_manager"


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: Optional[str] = None
    role: str = ROLE_SUPER_ADMIN
    store_id: Optional[str] = None
    store_code: Optional[str] = None
    store_name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(
        minutes=settings.get("auth.access_token_expire_minutes", 1440)
    ))
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.get("auth.secret_key"),
        algorithm=settings.get("auth.algorithm", "HS256"),
    )


def _store_context(session: Session, store_code: Optional[str]) -> dict:
    if not store_code:
        return {"store_id": None, "store_code": None, "store_name": None}
    store = session.query(StoreModel).filter(
        StoreModel.store_code == store_code,
        StoreModel.status == 1,
    ).first()
    if not store:
        return {"store_id": None, "store_code": store_code, "store_name": None}
    return {"store_id": store.id, "store_code": store.store_code, "store_name": store.store_name}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
):
    """获取当前用户上下文（依赖注入）"""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.get("auth.secret_key"),
            algorithms=[settings.get("auth.algorithm", "HS256")],
        )
        username: str = payload.get("sub")
        role: str = payload.get("role") or ROLE_SUPER_ADMIN
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证凭证")

        ctx = {
            "username": username,
            "role": role,
            "store_id": payload.get("store_id"),
            "store_code": payload.get("store_code"),
            "store_name": payload.get("store_name"),
        }
        if role == ROLE_STORE_MANAGER and not ctx["store_id"]:
            ctx.update(_store_context(session, ctx.get("store_code") or username))
        return ctx
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭证")


def require_super_admin(current_user: dict):
    if current_user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="权限不足")


def scoped_store_id(current_user: dict, requested_store_id: Optional[str] = None) -> Optional[str]:
    """按当前用户角色计算可访问的 store_id。"""
    if current_user.get("role") == ROLE_STORE_MANAGER:
        store_id = current_user.get("store_id")
        if not store_id:
            raise HTTPException(status_code=403, detail="未绑定门店")
        if requested_store_id and requested_store_id != store_id:
            raise HTTPException(status_code=403, detail="无权访问其他门店")
        return store_id
    return requested_store_id


def init_default_admin(session: Session):
    """初始化默认管理员账号"""
    admin = session.query(AdminUserModel).filter(
        AdminUserModel.username == settings.get("admin.username", "admin")
    ).first()
    if not admin:
        admin = AdminUserModel(
            id=str(hash("admin"))[:64],
            username=settings.get("admin.username", "admin"),
            password_hash=get_password_hash(settings.get("admin.password", "admin123")),
            display_name="管理员",
            role=ROLE_SUPER_ADMIN,
        )
        session.add(admin)
        session.commit()
        logger.info("默认管理员账号已创建")
