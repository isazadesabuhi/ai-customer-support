from collections.abc import Sequence
from typing import Protocol

from .configuration import LLMConfig
from .schemas import LLMMessage, LLMResponse


class LLMClient(Protocol):
    def generate(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse: ...


def get_llm_client(config: LLMConfig | None = None) -> LLMClient:
    config = config if config is not None else LLMConfig.from_environment()
    from .providers.openai import OpenAILLMClient

    return OpenAILLMClient(config)
