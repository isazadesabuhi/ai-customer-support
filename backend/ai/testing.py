"""Deterministic client for dependency injection in tests."""

from collections.abc import Sequence
from dataclasses import dataclass

from .errors import LLMError
from .schemas import LLMMessage, LLMResponse, validate_request


@dataclass(frozen=True, slots=True)
class LLMCall:
    messages: tuple[LLMMessage, ...]
    model: str | None
    temperature: float | None
    max_output_tokens: int | None


class FakeLLMClient:
    def __init__(self, outcome: LLMResponse | LLMError):
        self._outcome = outcome
        self.calls: list[LLMCall] = []

    def generate(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        messages = validate_request(
            messages,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        self.calls.append(LLMCall(messages, model, temperature, max_output_tokens))
        if isinstance(self._outcome, LLMError):
            raise self._outcome
        return self._outcome
