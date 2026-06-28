"""认证控制器 - 登录/获取用户信息"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import AdminUserModel, StoreModel
from app.interfaces.api.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ROLE_STORE_MANAGER,
    ROLE_SUPER_ADMIN,
    TokenResponse,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: Session = Depends(get_session),
):
    """管理员/店长登录"""
    user = session.query(AdminUserModel).filter(
        AdminUserModel.username == req.username,
        AdminUserModel.status == 1,
    ).first()

    if user:
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        store = None
        if user.role == ROLE_STORE_MANAGER:
            store = session.query(StoreModel).filter(
                StoreModel.store_code == user.username,
                StoreModel.status == 1,
            ).first()
            if not store:
                raise HTTPException(status_code=403, detail="店长账号未绑定门店")

        token_data = {"sub": user.username, "role": user.role or ROLE_SUPER_ADMIN}
        if store:
            token_data.update({
                "store_id": store.id,
                "store_code": store.store_code,
                "store_name": store.store_name,
            })
        access_token = create_access_token(data=token_data)

        return TokenResponse(
            access_token=access_token,
            username=user.username,
            display_name=user.display_name,
            role=user.role or ROLE_SUPER_ADMIN,
            store_id=store.id if store else None,
            store_code=store.store_code if store else None,
            store_name=store.store_name if store else None,
        )

    # 门店店长默认账号：门店编码 / 门店编码。首次登录时自动创建。
    if req.username == req.password and req.username.isdigit() and len(req.username) == 6:
        store = session.query(StoreModel).filter(
            StoreModel.store_code == req.username,
            StoreModel.status == 1,
        ).first()
        if not store:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user = AdminUserModel(
            id=f"store_manager_{store.store_code}",
            username=store.store_code,
            password_hash=get_password_hash(req.password),
            display_name=store.manager or store.store_name or store.store_code,
            role=ROLE_STORE_MANAGER,
            status=1,
        )
        session.add(user)
        session.commit()

        token_data = {
            "sub": user.username,
            "role": ROLE_STORE_MANAGER,
            "store_id": store.id,
            "store_code": store.store_code,
            "store_name": store.store_name,
        }
        access_token = create_access_token(data=token_data)
        return TokenResponse(
            access_token=access_token,
            username=user.username,
            display_name=user.display_name,
            role=ROLE_STORE_MANAGER,
            store_id=store.id,
            store_code=store.store_code,
            store_name=store.store_name,
        )

    raise HTTPException(status_code=401, detail="用户名或密码错误")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"code": 0, "msg": "success", "data": current_user}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """修改当前登录用户密码"""
    user = session.query(AdminUserModel).filter(
        AdminUserModel.username == current_user["username"],
        AdminUserModel.status == 1,
    ).first()
    if not user or not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="原密码错误")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")

    user.password_hash = get_password_hash(req.new_password)
    session.commit()
    return {"code": 0, "msg": "success"}
