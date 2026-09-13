"""
config.py — Application-wide configuration loaded from environment variables.
All settings have sensible defaults for local development.
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

    # ── LLM ────────────────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # ── NLP ────────────────────────────────────────────────────────────────────
    spacy_model: str = "en_core_web_trf"
    spacy_model_fallback: str = "en_core_web_sm"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton of Settings."""
    s = Settings()
    # Generate a random secret key if none was provided via env
    if not s.secret_key:
        s.secret_key = secrets.token_urlsafe(64)
    return s


settings = get_settings()
