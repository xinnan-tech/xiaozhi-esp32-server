from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from services.user_service import user_service
from schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    PasswordUpdateRequest,
    UserInfo
)
from utils.response import success_response
from api.auth import get_current_user_id
from repositories import UserModel

router = APIRouter()


@router.post("/register", summary="Register a new user account under live agent system")
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account"""
    await user_service.register(
        db=db,
        username=request.username,
        password=request.password
    )
    return success_response(message="User account registered successfully")


@router.post("/login", summary="User Login for a token")
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """User login for a token"""
    login_response = await user_service.login(
        db=db,
        username=request.username,
        password=request.password
    )
    return success_response(data=login_response.model_dump())


@router.get("/info", summary="Get User Info")
async def get_user_info(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information"""

    user: UserModel = await user_service.get_user_info(db=db, user_id=current_user_id)

    user_info = UserInfo(
        user_id=user.user_id,
        username=user.username,
        created_at=user.created_at
    )
    return success_response(data=user_info.model_dump())


@router.post("/password", summary="Update Password")
async def update_password(
    request: PasswordUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update user password"""
    await user_service.update_password(
        db=db,
        user_id=current_user_id,
        old_password=request.old_password,
        new_password=request.new_password
    )
    return success_response(message="Password updated successfully")


@router.post("/logout", summary="User Logout")
async def logout(
    token: str = Header(..., description="Authentication token"),
    db: AsyncSession = Depends(get_db)
):
    """User logout"""
    await user_service.logout(db=db, token=token)
    return success_response(message="Logout successful")

