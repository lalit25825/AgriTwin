"""Password hashing using bcrypt's stable public API.

Stored hashes use the standard $2b$ bcrypt format, so existing hashes produced
by Passlib's bcrypt handler remain verifiable with bcrypt.checkpw.
"""
import bcrypt


_MAX_BCRYPT_BYTES = 72


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_BCRYPT_BYTES:
        raise ValueError("Password is too long for bcrypt; use at most 72 UTF-8 bytes.")
    return encoded


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash for a new password."""
    hashed = bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a password against a stored standard bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False
