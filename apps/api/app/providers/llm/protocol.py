from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.providers.llm.models import LLMGenerationRequest

StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class LLMProvider(Protocol):
    """Vendor-independent structured generation contract."""

    name: str
    model: str | None

    async def generate_structured(
        self, request: LLMGenerationRequest, response_schema: type[StructuredResponse]
    ) -> StructuredResponse: ...
