from functools import lru_cache

from app.core.config import get_settings
from app.providers.llm.openai.provider import OpenAIProvider
from app.providers.llm.protocol import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider != "openai":
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return OpenAIProvider(settings.openai_api_key, settings.llm_model)
