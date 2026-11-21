"""
Authentication-related custom exceptions.
"""


class AuthenticationException(Exception):
    """
    Base exception for all authentication-related exceptions.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UsernameAlreadyExistsError(AuthenticationException):
    """
    Raised when a username already exists.
    """

    def __init__(self):
        super().__init__("Username already exists.")


class EmailAlreadyExistsError(AuthenticationException):
    """
    Raised when an email already exists.
    """

    def __init__(self):
        super().__init__("Email already exists.")


class PhoneAlreadyExistsError(AuthenticationException):
    """
    Raised when a phone number already exists.
    """

    def __init__(self):
        super().__init__("Phone number already exists.")


class InvalidCredentialsError(AuthenticationException):
    """
    Raised when login credentials are invalid.
    """

    def __init__(self):
        super().__init__("Invalid username/email or password.")


class InactiveUserError(AuthenticationException):
    """
    Raised when an inactive user attempts to authenticate.
    """

    def __init__(self):
        super().__init__("User account is inactive.")


class InvalidTokenError(AuthenticationException):
    """
    Raised when a JWT token is invalid.
    """

    def __init__(self):
        super().__init__("Invalid authentication token.")


class TokenExpiredError(AuthenticationException):
    """
    Raised when a JWT token has expired.
    """

    def __init__(self):
        super().__init__("Authentication token has expired.")


class UnauthorizedError(AuthenticationException):
    """
    Raised when authentication is required.
    """

    def __init__(self):
        super().__init__("Authentication required.")


class ForbiddenError(AuthenticationException):
    """
    Raised when a user does not have permission.
    """

    def __init__(self):
        super().__init__("You do not have permission to perform this action.")