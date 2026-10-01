import asyncio
from types import SimpleNamespace

from app.providers.llm.models import LLMGenerationRequest
from app.providers.llm.openai.provider import OpenAIProvider
from app.scripts.schemas import ScriptDraft


class FakeStructuredParser:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        draft = ScriptDraft.model_validate(
            {
                "language": "es",
                "hooks": [],
                "recommended_hook_index": 0,
                "title": "Título",
                "first_screen_text": "Texto",
                "script": "El Barça está listo.",
                "segments": [],
                "caption": "",
                "comment_question": "",
                "hashtags": [],
                "mentioned_entities": [],
            }
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, parsed=draft))]
        )


def test_openai_adapter_uses_structured_output_at_the_provider_boundary() -> None:
    parser = FakeStructuredParser()
    client = SimpleNamespace(chat=SimpleNamespace(completions=parser))
    provider = OpenAIProvider("test-key", "configured-model", client=client)

    result = asyncio.run(
        provider.generate_structured(
            LLMGenerationRequest("system", "user", "postmatch_script_v1"), ScriptDraft
        )
    )

    assert result.language == "es"
    assert parser.kwargs["model"] == "configured-model"
    assert parser.kwargs["response_format"] is ScriptDraft
