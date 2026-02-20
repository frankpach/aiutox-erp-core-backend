"""Application configuration loaded from environment variables."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import ConfigDict, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    ENV: str = "dev"
    DEBUG: bool = True

    # Database connection components
    # Defaults are for local development (outside Docker)
    # When running in Docker, these should be overridden by .env file
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 15432  # Default to mapped port for local development
    POSTGRES_USER: str = "devuser"
    POSTGRES_PASSWORD: str = "devpass"
    POSTGRES_DB: str = "aiutox_erp_dev"

    # Allow DATABASE_URL to be set directly, or construct from components
    DATABASE_URL: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        """Get database URL, either from DATABASE_URL env var or construct from components."""
        # If DATABASE_URL is explicitly set, use it (highest priority)
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Otherwise, construct from individual components
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

    # Redis Streams configuration
    REDIS_STREAM_DOMAIN: str = "events:domain"
    REDIS_STREAM_TECHNICAL: str = "events:technical"
    REDIS_STREAM_FAILED: str = "events:failed"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_REMEMBER_ME_DAYS: int = 30

    # Initial owner bootstrap (used by AdminUserSeeder)
    INITIAL_OWNER_EMAIL: str = "owner@aiutox.com"
    INITIAL_OWNER_PASSWORD: str = "password"
    INITIAL_OWNER_FULL_NAME: str = "System Owner"

    # Cookie Configuration
    COOKIE_SECURE: bool = True  # Only HTTPS in production
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None

    # API URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:3000"
    )

    # SSE (Server-Sent Events) Configuration
    SSE_TIMEOUT: int = 3600  # Timeout in seconds (default: 1 hour)
    SSE_HEARTBEAT_INTERVAL: int = 30  # Heartbeat interval in seconds (default: 30s)

    # Logging
    LOG_LEVEL: str = "INFO"  # INFO for dev, WARNING for prod
    LOG_TO_FILE: bool = False  # False for dev, True for prod
    LOG_TO_DB: bool = True  # Always log to database
    LOG_FORMAT: str = "human"  # "human" for dev, "json" for prod

    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@aiutox.com"
    SMTP_USE_TLS: bool = True

    model_config = ConfigDict(
        env_file=[".env", "../.env"],  # Try .env in current dir first, then parent dir
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env that are not in Settings
    )

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
