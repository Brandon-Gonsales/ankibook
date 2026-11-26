from pathlib import Path
from typing import List, Optional
from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""

    PROJECT_NAME: str = "AnkiBook Backend API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API REST de AnkiBook desarrollada con FastAPI y SQLModel"
    API_V1_PREFIX: str = "/api/v1"
    # Safe by default: "development" (set explicitly in a local .env) enables
    # the X-User-Id login shortcut and must never be used on a public server.
    ENVIRONMENT: str = "production"
    DEBUG: bool = Field(default=False, validation_alias="ANKIBOOK_DEBUG")

    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_password"
    POSTGRES_DB: str = "ankibook"
    DATABASE_URL: Optional[str] = None

    # Firebase Admin credentials (private service-account JSON path)
    FIREBASE_CREDENTIALS_PATH: Optional[Path] = Field(
        default=None,
        validation_alias=AliasChoices(
            "FIREBASE_CREDENTIALS_PATH",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ),
    )
    FIREBASE_PROJECT_ID: Optional[str] = None

    # CORS origins. Empty when the frontend is served from the same domain
    # (reverse proxy); list the frontend URL here if it lives elsewhere.
    BACKEND_CORS_ORIGINS: List[str] = []

    # Database schema
    DB_SCHEMA: str = "public"

    # Study day. "Repasar" mixes in at most SRS_NEW_CARDS_PER_DAY never-seen
    # cards per user and day; the day starts at SRS_DAY_START_HOUR local time.
    SRS_NEW_CARDS_PER_DAY: int = Field(default=20, ge=0, le=1000)
    SRS_TIMEZONE: str = "America/La_Paz"
    SRS_DAY_START_HOUR: int = Field(default=4, ge=0, le=23)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        """Return the async database connection URI using psycopg driver."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.casefold() == "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
