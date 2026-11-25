import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from .errors import LLMInvalidRequestError, LLMInvalidResponseError

LLMRole = Literal["system", "developer", "user", "assistant"]
ROLES = ("system", "developer", "user", "assistant")
MIN_OUTPUT_TOKENS = 16
MAX_OUTPUT_TOKENS = 4096


def valid_model(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:-]{0,199}", value) is not None
    )


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: LLMRole
    content: str = field(repr=False)

    def __post_init__(self):
        if self.role not in ROLES:
            raise LLMInvalidRequestError("Unsupported LLM message role.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise LLMInvalidRequestError("LLM messages require nonblank text.")


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self):
        for count in (self.input_tokens, self.output_tokens, self.total_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise LLMInvalidResponseError(
                    "The provider returned invalid token usage."
                )


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str = field(repr=False)
    provider: str
    model: str | None
    usage: LLMUsage | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None


def validate_request(
    messages: Sequence[LLMMessage],
    *,
    model: str | None,
    temperature: float | None,
    max_output_tokens: int | None,
    token_limit: int = MAX_OUTPUT_TOKENS,
) -> tuple[LLMMessage, ...]:
    if (
        not isinstance(messages, Sequence)
        or not messages
        or any(not isinstance(message, LLMMessage) for message in messages)
    ):
        raise LLMInvalidRequestError("Provide at least one LLMMessage.")
    if model is not None and not valid_model(model):
        raise LLMInvalidRequestError("Provide a valid model identifier.")
    if temperature is not None and (
        type(temperature) not in (float, int) or not 0 <= temperature <= 2
    ):
        raise LLMInvalidRequestError("Temperature must be a number from 0 to 2.")
    if max_output_tokens is not None and (
        type(max_output_tokens) is not int
        or not MIN_OUTPUT_TOKENS <= max_output_tokens <= token_limit
    ):
        raise LLMInvalidRequestError(
            f"Output tokens must be an integer from {MIN_OUTPUT_TOKENS} to {token_limit}."
        )
    return tuple(messages)
