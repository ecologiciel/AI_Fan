from __future__ import annotations

from dataclasses import dataclass


class LLMProviderError(RuntimeError):
    """A safe, vendor-neutral error raised by an LLM provider."""


@dataclass(frozen=True)
class LLMGenerationRequest:
    system_prompt: str
    user_prompt: str
    prompt_version: str
