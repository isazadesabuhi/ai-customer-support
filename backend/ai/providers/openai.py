from collections.abc import Callable, Sequence
from email.utils import parsedate_to_datetime
from time import sleep, time

from httpx import Client
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from openai.types.responses import EasyInputMessageParam, Response, ResponseUsage

from ..configuration import OPENAI_PROVIDER, LLMConfig
from ..errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ..schemas import LLMMessage, LLMResponse, LLMUsage, validate_request

MAX_RETRY_DELAY_SECONDS = 10.0


class OpenAILLMClient:
    def __init__(
        self,
        config: LLMConfig,
        *,
        http_client: Client | None = None,
        sleeper: Callable[[float], None] = sleep,
    ):
        self._config = config
        self._sleep = sleeper
        try:
            self._sdk = OpenAI(
                api_key=config.api_key,
                base_url="https://api.openai.com/v1",
                timeout=config.timeout_seconds,
                max_retries=0,
                http_client=http_client,
            )
        except Exception:
            pass
        else:
            return
        raise LLMConfigurationError(
            "Could not initialize the OpenAI SDK. Check local network configuration."
        )

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
            token_limit=self._config.max_output_tokens,
        )
        if temperature is not None:
            raise LLMInvalidRequestError(
                "This OpenAI adapter uses the model's temperature defaults. Omit temperature."
            )

        inputs = [
            EasyInputMessageParam(role=message.role, content=message.content)
            for message in messages
        ]
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._sdk.responses.create(
                    model=model or self._config.model,
                    input=inputs,
                    max_output_tokens=max_output_tokens
                    or self._config.max_output_tokens,
                    store=False,
                )
            except Exception as exc:
                error = _translate_error(exc)
                delay = (
                    _retry_delay(exc, attempt)
                    if error.retryable and attempt < self._config.max_retries
                    else None
                )
            else:
                return _normalize(response)

            if delay is None:
                raise error
            self._sleep(delay)
        raise AssertionError("LLM retry loop exhausted without a result or error.")


def _translate_error(exc: Exception) -> LLMError:
    if isinstance(exc, APITimeoutError):
        return LLMTimeoutError("The OpenAI request timed out.", retryable=True)
    if isinstance(exc, APIConnectionError):
        return LLMConnectionError("Could not connect to OpenAI.", retryable=True)
    if isinstance(exc, APIResponseValidationError):
        return LLMInvalidResponseError("OpenAI returned an invalid response.")
    if isinstance(exc, APIStatusError):
        match exc.status_code:
            case 401 | 403:
                return LLMAuthenticationError(
                    "OpenAI denied credentials or access. Check the key and project permissions."
                )
            case 400 | 404 | 422:
                return LLMInvalidRequestError(
                    "OpenAI rejected the request. Check model access and request limits."
                )
            case 408:
                return LLMTimeoutError("The OpenAI request timed out.", retryable=True)
            case 429:
                if exc.code in {"insufficient_quota", "billing_hard_limit_reached"}:
                    return LLMRateLimitError(
                        "OpenAI quota is unavailable. Check project billing and limits."
                    )
                return LLMRateLimitError("OpenAI rate limit reached.", retryable=True)
            case 500 | 502 | 503 | 504:
                return LLMProviderError(
                    "OpenAI reported a temporary server error.", retryable=True
                )
    return LLMProviderError("The OpenAI request failed unexpectedly.")


def _retry_delay(exc: Exception, attempt: int) -> float | None:
    if isinstance(exc, APIStatusError):
        headers = exc.response.headers
        if headers.get("x-should-retry") == "false":
            return None
        delay = _retry_after(headers.get("retry-after-ms"), headers.get("retry-after"))
        if delay is not None:
            return delay if delay <= MAX_RETRY_DELAY_SECONDS else None
    return min(0.5 * 2**attempt, 2.0)


def _retry_after(milliseconds: str | None, seconds_or_date: str | None) -> float | None:
    for value, divisor in ((milliseconds, 1000), (seconds_or_date, 1)):
        if value is not None:
            try:
                delay = float(value) / divisor
            except ValueError:
                continue
            if 0 <= delay < float("inf"):
                return delay
    if seconds_or_date is not None:
        try:
            retry_at = parsedate_to_datetime(seconds_or_date)
            if retry_at.tzinfo is not None:
                return max(0.0, retry_at.timestamp() - time())
        except (ValueError, OverflowError, OSError):
            pass
    return None


def _normalize(response: Response) -> LLMResponse:
    if not isinstance(response, Response):
        raise LLMInvalidResponseError("OpenAI returned an invalid response.")

    if getattr(response, "status", None) not in (None, "completed"):
        raise LLMInvalidResponseError("OpenAI did not complete the response.")

    text = None
    try:
        text = response.output_text
    except (AttributeError, TypeError, ValueError):
        pass
    if not isinstance(text, str):
        raise LLMInvalidResponseError("OpenAI returned invalid text output.")
    if not text.strip():
        raise LLMInvalidResponseError("OpenAI returned no usable text.")

    usage = getattr(response, "usage", None)
    if usage is not None and not isinstance(usage, ResponseUsage):
        raise LLMInvalidResponseError("OpenAI returned invalid token usage.")

    return LLMResponse(
        text=text,
        provider=OPENAI_PROVIDER,
        model=_optional_string(getattr(response, "model", None)),
        usage=None
        if usage is None
        else LLMUsage(
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        ),
        provider_request_id=_optional_string(getattr(response, "_request_id", None)),
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
