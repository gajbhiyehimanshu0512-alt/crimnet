"""
ai/llm.py — Single place that decides which LLM backs the app.

Local development talks to Ollama. Setting GROQ_API_KEY switches every call
site (RAG answers, intelligence reports, relation extraction) to Groq's hosted
API, which is what a deployment without a GPU needs.

All callers use `.invoke(prompt)`, so both providers are drop-in compatible.
"""

import logging
from functools import lru_cache

from config import settings

logger = logging.getLogger(__name__)


def _provider() -> str:
    """Resolve 'auto' to groq when a key is present, otherwise ollama."""
    choice = (settings.llm_provider or "auto").strip().lower()
    if choice == "auto":
        return "groq" if settings.groq_api_key else "ollama"
    return choice


@lru_cache()
def get_llm():
    """Return a LangChain chat model. Cached — one instance per process."""
    provider = _provider()

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError(
                "GROQ_API_KEY is set but langchain-groq is not installed. "
                "Run: pip install langchain-groq"
            ) from exc
        if not settings.groq_api_key:
            raise RuntimeError("llm_provider=groq but GROQ_API_KEY is empty.")
        logger.info("LLM provider: groq (%s)", settings.groq_model)
        return ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model)

    from langchain_ollama import OllamaLLM

    logger.info("LLM provider: ollama (%s @ %s)", settings.ollama_model, settings.ollama_url)
    return OllamaLLM(base_url=settings.ollama_url, model=settings.ollama_model)


def describe_llm() -> str:
    """Human-readable provider + model, for API responses and error text."""
    if _provider() == "groq":
        return f"groq:{settings.groq_model}"
    return f"ollama:{settings.ollama_model}"


def reset_llm_cache() -> None:
    """Test hook — drop the cached instance so config changes take effect."""
    get_llm.cache_clear()
