from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import AuthProvider
from backend.app.exceptions.auth import (
    UsernameAlreadyExistsError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
    InvalidCredentialsError,
    InactiveUserError,
)
from backend.app.models.user import User
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
)
from backend.app.security.password import (
    hash_password,
    verify_password,
)


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    """
    Return a user by email.
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> User | None:
    """
    Return a user by username.
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_phone(
    db: AsyncSession,
    phone: str,
) -> User | None:
    """
    Return a user by phone number.
    """
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    return result.scalar_one_or_none()

async def get_user_by_id(
    db: AsyncSession,
    user_id: str,
) -> User | None:
    """
    Return a user by ID.
    """

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    return result.scalar_one_or_none()


async def get_user_by_identifier(
    db: AsyncSession,
    identifier: str,
) -> User | None:
    """
    Return a user by email or username.
    """

    identifier = identifier.strip().lower()

    result = await db.execute(
        select(User).where(
            or_(
                User.email == identifier,
                User.username == identifier,
            )
        )
    )

    return result.scalar_one_or_none()


def build_user(
    user_data: UserRegisterRequest,
) -> User:
    """
    Build a new User object without saving it.
    """

    return User(
        username=user_data.username.strip().lower(),
        full_name=user_data.full_name.strip(),
        email=user_data.email.strip().lower(),
        phone=user_data.phone.strip(),
        password_hash=hash_password(user_data.password),
        auth_provider=AuthProvider.LOCAL,
        role=user_data.role,
    )


async def create_user(
    db: AsyncSession,
    user_data: UserRegisterRequest,
) -> User:
    """
    Persist a new user.
    """

    user = build_user(user_data)

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    except Exception:
        await db.rollback()
        raise


async def register_user(
    db: AsyncSession,
    user_data: UserRegisterRequest,
) -> User:
    """
    Register a new user.
    """

    normalized_username = user_data.username.strip().lower()
    normalized_email = user_data.email.strip().lower()
    normalized_phone = user_data.phone.strip()

    if await get_user_by_username(db, normalized_username):
        raise UsernameAlreadyExistsError()

    if await get_user_by_email(db, normalized_email):
        raise EmailAlreadyExistsError()

    if await get_user_by_phone(db, normalized_phone):
        raise PhoneAlreadyExistsError()

    return await create_user(db, user_data)


async def login_user(
    db: AsyncSession,
    login_data: UserLoginRequest,
) -> User:
    """
    Authenticate a user using email or username.
    """

    user = await get_user_by_identifier(
        db,
        login_data.identifier,
    )

    if not user:
        raise InvalidCredentialsError()

    if not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    return user