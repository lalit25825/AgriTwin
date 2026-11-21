"""
Global exception handlers for the application.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.app.exceptions.auth import (
    UsernameAlreadyExistsError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
    InvalidCredentialsError,
    InactiveUserError,
    InvalidTokenError,
    TokenExpiredError,
    UnauthorizedError,
    ForbiddenError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers.
    """

    @app.exception_handler(UsernameAlreadyExistsError)
    async def username_exists_handler(
        request: Request,
        exc: UsernameAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(EmailAlreadyExistsError)
    async def email_exists_handler(
        request: Request,
        exc: EmailAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(PhoneAlreadyExistsError)
    async def phone_exists_handler(
        request: Request,
        exc: PhoneAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        request: Request,
        exc: InvalidCredentialsError,
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(
        request: Request,
        exc: InactiveUserError,
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        request: Request,
        exc: InvalidTokenError,
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
        )

    @app.exception_handler(TokenExpiredError)
    async def token_expired_handler(
        request: Request,
        exc: TokenExpiredError,
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(
        request: Request,
        exc: UnauthorizedError,
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(
        request: Request,
        exc: ForbiddenError,
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )