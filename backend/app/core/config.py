from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at backend/app/core/config.py
# Path(__file__).parents: [0] core/  [1] app/  [2] backend/  [3] repo-root
_ENV_FILE = str(Path(__file__).resolve().parents[3] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently drop frontend-only vars (NEXT_PUBLIC_*)
        env_ignore_empty=True,
    )

    # Application — DEBUG has a safe universal default; SECRET_KEY must be set explicitly
    debug: bool = False
    secret_key: str = Field(..., description="Django/FastAPI secret key — set in .env")

    # Database — credentials and URL must come from the environment
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(..., description="PostgreSQL database name")
    database_url: str = Field(..., description="Full async DB connection URL")

    # JWT — secret must be set explicitly; lifetimes have sensible universal defaults
    jwt_secret_key: str = Field(..., description="JWT signing secret — set in .env")
    jwt_access_token_lifetime: int = 15  # minutes
    jwt_refresh_token_lifetime: int = 10080  # minutes (7 days)

    # OpenAI — optional; empty string disables AI features gracefully
    LITELLM_API_KEY: str = ""
    LITELLM_BASE_URL: str = ""

    # CORS — comma-separated list of allowed origins; defaults to localhost dev ports
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    # LangSmith tracing — optional; set LANGCHAIN_TRACING_V2=true to enable
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "wizly-ai-twin"

    @property
    def cors_origins(self) -> list[str]:
        """Return ALLOWED_ORIGINS split and stripped."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def __repr__(self) -> str:
        """Never print secret values if settings is accidentally logged."""
        return (
            f"Settings(debug={self.debug}, database_url=<redacted>, "
            f"jwt_secret_key=<redacted>, litellm_api_key=<redacted>)"
        )

    # Embeddings — model name has a stable default; can be overridden in .env
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # ChromaDB — path differs between local and Docker; override in .env
    chroma_persist_dir: str = Field(..., description="ChromaDB persistence directory")

    # S3 / LocalStack — all values must come from .env
    aws_access_key_id: str = Field(..., description="AWS / LocalStack access key")
    aws_secret_access_key: str = Field(..., description="AWS / LocalStack secret key")
    aws_default_region: str = Field(..., description="AWS region")
    aws_endpoint_url: str = Field(..., description="S3 endpoint (http://localhost:4566 for LocalStack)")
    s3_bucket_name: str = Field(..., description="S3 bucket for document uploads")


settings = Settings()
