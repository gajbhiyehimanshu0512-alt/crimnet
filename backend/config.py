"""
config.py — Application-wide configuration loaded from environment variables.
All settings have sensible defaults for local development.
Cloud deployment settings (Groq, etc.) are added for production.
"""

import secrets
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────────────
    app_env: str = "development"
    secret_key: str = ""  # Generated at startup if empty
    upload_dir: str = "./uploads"
    max_upload_mb: int = 50

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins for production
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Neo4j ──────────────────────────────────────────────────────────────────
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cna_password123"

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    postgres_url: str = "postgresql://cna_user:cna_pass@localhost:5432/criminal_network"

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── ChromaDB ───────────────────────────────────────────────────────────────
    chroma_url: str = "http://localhost:8001"
    chroma_collection: str = "criminal_documents"
    # Set USE_CHROMA=false to disable ChromaDB (for cloud deployments without it)
    use_chroma: bool = True

    # ── LLM ────────────────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    # Groq — free cloud LLM API (replaces Ollama in cloud deployments)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-70b-8192"

    # ── NLP ────────────────────────────────────────────────────────────────────
    spacy_model: str = "en_core_web_trf"
    spacy_model_fallback: str = "en_core_web_sm"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_provider(self) -> str:
        """Auto-detect which LLM provider to use based on available keys."""
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "ollama"


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton of Settings."""
    s = Settings()
    # Generate a random secret key if none was provided via env
    if not s.secret_key:
        s.secret_key = secrets.token_urlsafe(64)
    return s


settings = get_settings()
