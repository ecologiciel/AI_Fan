from __future__ import annotations

from typing import Any, TypeVar, cast

from pydantic import BaseModel

from app.providers.llm.models import LLMGenerationRequest, LLMProviderError

StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class OpenAIProvider:
    """OpenAI adapter using the official SDK structured-output parser only here."""

    name = "openai"

    def __init__(self, api_key: str | None, model: str | None, client: Any | None = None) -> None:
        self.model = model
        self._api_key = api_key
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key or not self.model:
            raise LLMProviderError(
                "OpenAI is not configured: OPENAI_API_KEY and LLM_MODEL are required"
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as error:  # pragma: no cover - exercised by deployment dependency check
            raise LLMProviderError("OpenAI SDK is not installed") from error
        self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate_structured(
        self, request: LLMGenerationRequest, response_schema: type[StructuredResponse]
    ) -> StructuredResponse:
        if not self.model:
            raise LLMProviderError("OpenAI is not configured: LLM_MODEL is required")
        try:
            completion = await self._get_client().chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                response_format=response_schema,
            )
            message = completion.choices[0].message
        except LLMProviderError:
            raise
        except Exception as error:  # noqa: BLE001 - SDK exceptions stay at the provider boundary
            raise LLMProviderError("OpenAI structured generation failed") from error
        if getattr(message, "refusal", None):
            raise LLMProviderError("OpenAI refused the generation request")
        parsed = getattr(message, "parsed", None)
        if parsed is None:
            raise LLMProviderError("OpenAI returned no structured content")
        return cast(StructuredResponse, parsed)
