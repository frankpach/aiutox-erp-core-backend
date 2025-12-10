"""Application configuration loaded from environment variables."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    ENV: str = "dev"
    DEBUG: bool = True

    # Database connection components
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "root"
    POSTGRES_PASSWORD: str = "pass"
    POSTGRES_DB: str = "aiutox_core_db"

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from individual components."""
        # URL encode password in case it contains special characters
        # Ensure password is a string and handle encoding properly
        # Convert to bytes first if needed, then to string to ensure proper encoding
        try:
            password_str = str(self.POSTGRES_PASSWORD)
            # Ensure it's properly encoded as UTF-8
            if isinstance(self.POSTGRES_PASSWORD, bytes):
                password_str = self.POSTGRES_PASSWORD.decode("utf-8", errors="replace")
            else:
                # Try to encode and decode to ensure it's valid UTF-8
                password_bytes = password_str.encode("utf-8", errors="replace")
                password_str = password_bytes.decode("utf-8", errors="replace")
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Fallback: use the string representation
            password_str = str(self.POSTGRES_PASSWORD)

        encoded_password = quote_plus(password_str, safe="")
        # Also encode user, host, and db name in case they have special chars
        encoded_user = quote_plus(str(self.POSTGRES_USER), safe="")
        encoded_host = quote_plus(str(self.POSTGRES_HOST), safe="")
        encoded_db = quote_plus(str(self.POSTGRES_DB), safe="")
        return (
            f"postgresql+psycopg2://{encoded_user}:{encoded_password}"
            f"@{encoded_host}:{self.POSTGRES_PORT}/{encoded_db}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Logging
    LOG_LEVEL: str = "INFO"  # INFO for dev, WARNING for prod
    LOG_TO_FILE: bool = False  # False for dev, True for prod
    LOG_TO_DB: bool = True  # Always log to database
    LOG_FORMAT: str = "human"  # "human" for dev, "json" for prod

    class Config:
        env_file = "../.env"  # .env file is in the project root
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that are not in Settings

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> str:
            """Parse environment variable, handling encoding issues."""
            if raw_val is None:
                return ""
            # Try to decode as UTF-8, fallback to latin-1 if needed
            if isinstance(raw_val, bytes):
                try:
                    return raw_val.decode("utf-8")
                except UnicodeDecodeError:
                    return raw_val.decode("latin-1")
            return str(raw_val)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
