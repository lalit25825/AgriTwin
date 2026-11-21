import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from backend.app.security.jwt import create_access_token
from backend.app.services.auth_service import (
    login_user,
    register_user,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    """
    return await register_user(db, user_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return a JWT access token.
    """

    user = await login_user(
        db,
        login_data,
    )

    access_token = create_access_token(
    {
        "sub": str(user.id),
        "type": "access",
    }
)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )