from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["local", "staging", "production"] = "local"
    APP_NAME: str = "Enterprise Knowledge Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://ekip_user:ekip_password@localhost:5432/ekip_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication & Security
    JWT_SECRET: str = "ekip-super-secure-jwt-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Vector Embeddings
    EMBEDDING_PROVIDER: Literal["mock", "fastembed"] = "mock"
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIM: int = 1024

    # LLM Generation & Resilience
    LLM_PROVIDER: Literal["mock", "gemini"] = "mock"
    LLM_MODEL: str = "gemini-1.5-flash"
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
