from functools import lru_cache
from typing import Literal
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["local", "staging", "production"] = "local"
    APP_NAME: str = "Enterprise Knowledge Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://ekip_user:ekip_password@localhost:5432/ekip_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Authentication & Security
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Vector Embeddings
    EMBEDDING_PROVIDER: Literal["mock", "fastembed"] = "mock"
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIM: int = 1024

    # LLM Generation & Resilience
    LLM_PROVIDER: Literal["mock", "gemini"] = "mock"
    LLM_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_API_KEY: str | None = None

    # Reranking & Context Compression
    RERANKER_PROVIDER: Literal["mock", "fastembed"] = "mock"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANK_TOP_N: int = 5
    ENABLE_CONTEXT_COMPRESSION: bool = True

    # Query Transformation
    DEFAULT_QUERY_TRANSFORMATION: Literal["none", "hyde", "expansion", "rewrite", "mock"] = "none"

    # Semantic Caching Layer
    ENABLE_SEMANTIC_CACHE: bool = True
    SEMANTIC_CACHE_PROVIDER: Literal["redis", "inmemory"] = "redis"
    SEMANTIC_CACHE_THRESHOLD: float = 0.92
    SEMANTIC_CACHE_TTL_SECONDS: int = 86400

    # Background Ingestion Queue
    UPLOAD_DIR: str = "data/uploads"
    INGESTION_QUEUE_NAME: str = "ekip:ingestion_jobs"

    # Rate Limiting
    RATE_LIMIT_QUERY_PER_MINUTE: int = 20
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 10

    # Ingestion Worker Settings
    RUN_IN_PROCESS_WORKER: bool = True  # Free-tier default: runs inside web server; set False for standalone worker

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
            if "&channel_binding=require" in v:
                v = v.replace("&channel_binding=require", "")
        return v

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        if self.APP_ENV == "production":
            if not self.JWT_SECRET:
                raise ValueError("JWT_SECRET must be set in production environment")
            if len(self.JWT_SECRET) < 32:
                raise ValueError(
                    f"JWT_SECRET is too weak (length {len(self.JWT_SECRET)} is less than 32 characters in production)"
                )
            weak_secrets = {
                "secret",
                "changeme",
                "password",
                "ekip-super-secure-jwt-secret-key-change-in-production-2026",
            }
            if self.JWT_SECRET.lower() in weak_secrets:
                raise ValueError("JWT_SECRET cannot use default or insecure placeholder in production")
        elif not self.JWT_SECRET:
            self.JWT_SECRET = "dev-insecure-secret-local-testing-only-32chars"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
