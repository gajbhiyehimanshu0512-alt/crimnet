"""
ai/llm.py — Single place that decides which LLM backs the app.

Local development talks to Ollama. Setting GROQ_API_KEY switches every call
site (RAG answers, intelligence reports, relation extraction) to Groq's hosted
API, which is what a deployment without a GPU needs.

Groq is driven through the raw `groq` SDK rather than `langchain-groq`, because
langchain-groq >= 0.3 requires langchain-core >= 0.3 while this project pins
langchain==0.2.1 (which requires langchain-core < 0.3). Installing both makes
the resolver fail and the whole build collapses.

All callers use `.invoke(prompt)`, so every provider is drop-in compatible.
"""

import logging
from functools import lru_cache

from config import settings

logger = logging.getLogger(__name__)


def _provider() -> str:
    """Resolve which provider to use from settings (a property, never 'auto')."""
    return (settings.llm_provider or "ollama").strip().lower()


class GroqLLM:
    """Minimal `.invoke(prompt)` wrapper around the Groq chat completions API."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        from groq import Groq  # imported lazily so Ollama-only setups skip it

        self._client = Groq(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def invoke(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self._max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""


@lru_cache()
def get_llm():
    """Return an LLM client. Cached — one instance per process."""
    provider = _provider()

    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("LLM provider is 'groq' but GROQ_API_KEY is empty.")
        logger.info("LLM provider: groq (%s)", settings.groq_model)
        return GroqLLM(api_key=settings.groq_api_key, model=settings.groq_model)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise RuntimeError("LLM provider is 'openai' but OPENAI_API_KEY is empty.")
        logger.info("LLM provider: openai (gpt-4o-mini)")
        return ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4o-mini", temperature=0.1)

    from langchain_ollama import OllamaLLM

    logger.info("LLM provider: ollama (%s @ %s)", settings.ollama_model, settings.ollama_url)
    return OllamaLLM(base_url=settings.ollama_url, model=settings.ollama_model)


def describe_llm() -> str:
    """Human-readable provider + model, for API responses and error text."""
    provider = _provider()
    if provider == "groq":
        return f"groq:{settings.groq_model}"
    if provider == "openai":
        return "openai:gpt-4o-mini"
    return f"ollama:{settings.ollama_model}"


def reset_llm_cache() -> None:
    """Test hook — drop the cached instance so config changes take effect."""
    get_llm.cache_clear()
