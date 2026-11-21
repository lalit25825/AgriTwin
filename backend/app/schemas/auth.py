import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.core.enums import UserRole


class UserRegisterRequest(BaseModel):
    full_name: str = Field(
        min_length=3,
        max_length=100,
    )

    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
    )

    email: EmailStr

    phone: str = Field(
        min_length=10,
        max_length=20,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole

    @field_validator("password")
    @classmethod
    def bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class UserLoginRequest(BaseModel):
    """
    Request schema for user login using either
    email or username.
    """

    identifier: str = Field(
        min_length=3,
        max_length=100,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("password")
    @classmethod
    def bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    email: EmailStr
    phone: str
    role: UserRole
    is_active: bool
    is_verified: bool