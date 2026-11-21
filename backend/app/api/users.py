from fastapi import APIRouter, Depends

from backend.app.models.user import User
from backend.app.schemas.auth import UserResponse
from backend.app.security.dependencies import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently authenticated user.
    """

    return current_user