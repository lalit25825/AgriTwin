from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.exceptions.auth import (
    ForbiddenError,
    InactiveUserError,
    InvalidTokenError,
    UnauthorizedError,
)
from backend.app.models.user import User
from backend.app.security.jwt import decode_access_token
from backend.app.services.auth_service import get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Return the currently authenticated user.
    """

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise InvalidTokenError()

    if payload.get("type") != "access":
        raise InvalidTokenError()

    user_id = payload.get("sub")

    if not user_id:
        raise InvalidTokenError()

    user = await get_user_by_id(
        db,
        user_id,
    )

    if not user:
        raise UnauthorizedError()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Return the currently authenticated active user.
    """

    if not current_user.is_active:
        raise InactiveUserError()

    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Create a dependency that allows access only to users
    having one of the specified roles.
    """

    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:

        if current_user.role not in allowed_roles:
            raise ForbiddenError()

        return current_user

    return role_checker


# Role-specific dependencies

get_current_admin = require_role(UserRole.ADMIN)

get_current_farmer = require_role(UserRole.FARMER)

get_current_buyer = require_role(UserRole.BUYER)

get_current_fpo = require_role(UserRole.FPO)

get_current_transporter = require_role(UserRole.TRANSPORTER)

get_current_storage_provider = require_role(
    UserRole.STORAGE_PROVIDER,
)