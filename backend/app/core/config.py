from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # Application
    # =========================
    app_name: str = "AgriTwin API"
    app_env: str = "development"
    debug: bool = True

    # =========================
    # Security
    # =========================
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # =========================
    # PostgreSQL
    # =========================
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # =========================
    # Redis
    # =========================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()