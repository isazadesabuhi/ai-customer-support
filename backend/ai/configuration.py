import os
from dataclasses import dataclass, field

from .errors import LLMConfigurationError
from .schemas import MAX_OUTPUT_TOKENS, MIN_OUTPUT_TOKENS, valid_model

OPENAI_PROVIDER = "openai"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2
DEFAULT_OUTPUT_TOKENS = 500


@dataclass(frozen=True, slots=True)
class LLMConfig:
    model: str
    api_key: str = field(repr=False)
    provider: str = OPENAI_PROVIDER
    timeout_seconds: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_RETRIES
    max_output_tokens: int = DEFAULT_OUTPUT_TOKENS

    def __post_init__(self):
        if self.provider != OPENAI_PROVIDER:
            raise LLMConfigurationError("LLM_PROVIDER must be openai.")
        if (
            not isinstance(self.api_key, str)
            or not self.api_key
            or any(not 33 <= ord(character) <= 126 for character in self.api_key)
        ):
            raise LLMConfigurationError(
                "Set OPENAI_API_KEY to a nonempty API key without whitespace."
            )
        if not valid_model(self.model) or self.model == self.api_key:
            raise LLMConfigurationError("Set OPENAI_MODEL to a valid model identifier.")
        if (
            type(self.timeout_seconds) not in (float, int)
            or not 0 < self.timeout_seconds <= 120
        ):
            raise LLMConfigurationError(
                "LLM_TIMEOUT_SECONDS must be greater than 0 and at most 120."
            )
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 3:
            raise LLMConfigurationError(
                "LLM_MAX_RETRIES must be an integer from 0 to 3."
            )
        if (
            type(self.max_output_tokens) is not int
            or not MIN_OUTPUT_TOKENS <= self.max_output_tokens <= MAX_OUTPUT_TOKENS
        ):
            raise LLMConfigurationError(
                f"LLM_MAX_OUTPUT_TOKENS must be an integer from {MIN_OUTPUT_TOKENS} to {MAX_OUTPUT_TOKENS}."
            )

    @classmethod
    def from_environment(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("LLM_PROVIDER", OPENAI_PROVIDER),
            model=os.getenv("OPENAI_MODEL", ""),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            timeout_seconds=_number("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT, float),
            max_retries=_number("LLM_MAX_RETRIES", DEFAULT_RETRIES, int),
            max_output_tokens=_number(
                "LLM_MAX_OUTPUT_TOKENS", DEFAULT_OUTPUT_TOKENS, int
            ),
        )


def _number[T: (int, float)](name: str, default: T, parse: type[T]) -> T:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return parse(value)
    except ValueError:
        pass
    raise LLMConfigurationError(f"{name} must be a valid {parse.__name__}.")
