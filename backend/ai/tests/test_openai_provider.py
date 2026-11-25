import json
from email.utils import formatdate

import httpx
import pytest

from ai.configuration import LLMConfig
from ai.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ai.providers.openai import OpenAILLMClient
from ai.schemas import LLMMessage, LLMResponse, LLMUsage

MESSAGES = [LLMMessage("user", "  Fictional sample prompt.  ")]


def reply(**fields):
    body = {
        "object": "response",
        "id": "resp_test",
        "model": "example-snapshot",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "id": "msg_test",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": "  READY  ", "annotations": []}
                ],
            },
        ],
        "usage": {"input_tokens": 8, "output_tokens": 2, "total_tokens": 10},
    }
    body.update(fields)
    return httpx.Response(200, json=body)


def failure(status, headers=None, code=None):
    return httpx.Response(
        status,
        headers=headers,
        json={"error": {"message": "SECRET debug details", "code": code}},
    )


@pytest.fixture
def sdk_client():
    def build(outcomes, **options):
        queue = iter(outcomes)
        requests = []
        delays = []

        def handler(request):
            requests.append(request)
            outcome = next(queue)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return (
            OpenAILLMClient(
                LLMConfig(model="configured-model", api_key="unit-test-key", **options),
                http_client=httpx.Client(transport=httpx.MockTransport(handler)),
                sleeper=delays.append,
            ),
            requests,
            delays,
        )

    return build


def test_responses_sdk_sends_roles_timeout_and_explicit_limits(sdk_client, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://elsewhere.example.com/v1")
    response = reply()
    response.headers["x-request-id"] = "req_test"
    client, requests, delays = sdk_client(
        [response], timeout_seconds=9.25, max_output_tokens=192
    )
    messages = [
        LLMMessage("system", "Context"),
        LLMMessage("developer", "Instructions"),
        *MESSAGES,
        LLMMessage("assistant", "Previous reply"),
    ]

    result = client.generate(messages, model="override-model", max_output_tokens=40)

    assert len(requests) == 1 and delays == []
    request = requests[0]
    assert (request.method, str(request.url)) == (
        "POST",
        "https://api.openai.com/v1/responses",
    )
    assert set(request.extensions["timeout"].values()) == {9.25}
    assert json.loads(request.content) == {
        "input": [{"role": m.role, "content": m.content} for m in messages],
        "model": "override-model",
        "max_output_tokens": 40,
        "store": False,
    }
    assert result == LLMResponse(
        "  READY  ", "openai", "example-snapshot", LLMUsage(8, 2, 10), "req_test"
    )


@pytest.mark.parametrize(
    "usage, expected", [(None, None), ({"output_tokens": 2}, LLMUsage(output_tokens=2))]
)
def test_default_model_and_missing_metadata(sdk_client, usage, expected):
    client, requests, _ = sdk_client([reply(usage=usage, model=None)])
    result = client.generate(MESSAGES)

    payload = json.loads(requests[0].content)
    assert payload["model"] == "configured-model"
    assert payload["max_output_tokens"] == 500
    assert result.usage == expected
    assert result.model is None
    assert result.provider_request_id is None and result.finish_reason is None


@pytest.mark.parametrize(
    "options", [{"temperature": 0.2}, {"max_output_tokens": 65}, {"model": " "}]
)
def test_invalid_or_model_dependent_options_fail_before_transport(sdk_client, options):
    client, requests, delays = sdk_client([], max_output_tokens=64)
    with pytest.raises(LLMInvalidRequestError):
        client.generate(MESSAGES, **options)
    assert requests == delays == []


@pytest.mark.parametrize(
    "response, message",
    [
        (reply(output=[]), "no usable text"),
        (
            reply(
                output=[
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "private refusal"}],
                    }
                ]
            ),
            "no usable text",
        ),
        (reply(status="incomplete"), "did not complete"),
        (reply(output=None), "invalid text output"),
        (reply(usage={"input_tokens": -8}), "invalid token usage"),
    ],
)
def test_unusable_response_has_sanitized_error_and_no_retry(
    sdk_client, response, message
):
    client, requests, delays = sdk_client([response])
    with pytest.raises(LLMInvalidResponseError, match=message) as exc:
        client.generate(MESSAGES)
    assert "private refusal" not in str(exc.value)
    assert len(requests) == 1 and delays == []


@pytest.mark.parametrize(
    "status, code, category",
    [
        (401, None, LLMAuthenticationError),
        (403, None, LLMAuthenticationError),
        (400, None, LLMInvalidRequestError),
        (404, None, LLMInvalidRequestError),
        (422, None, LLMInvalidRequestError),
        (429, "insufficient_quota", LLMRateLimitError),
        (409, None, LLMProviderError),
        (501, None, LLMProviderError),
    ],
)
def test_permanent_failures_are_sanitized_and_never_retried(
    sdk_client, status, code, category, caplog
):
    client, requests, delays = sdk_client(
        [failure(status, {"x-should-retry": "true"}, code)]
    )
    with pytest.raises(category) as exc:
        client.generate(MESSAGES)
    assert exc.value.retryable is False
    assert exc.value.__context__ is None
    for secret in ("SECRET", "unit-test-key", MESSAGES[0].content.strip()):
        assert secret not in str(exc.value) and secret not in caplog.text
    assert len(requests) == 1 and delays == []


@pytest.mark.parametrize(
    "remote_failure, category",
    [
        (httpx.ReadTimeout("secret"), LLMTimeoutError),
        (httpx.ConnectError("secret"), LLMConnectionError),
        (failure(503), LLMProviderError),
        (failure(429), LLMRateLimitError),
    ],
)
def test_transient_failure_can_recover_and_exhaustion_preserves_category(
    sdk_client, remote_failure, category
):
    client, requests, delays = sdk_client([remote_failure, reply()], max_retries=1)
    assert client.generate(MESSAGES).text == "  READY  "
    assert len(requests) == 2 and delays == [0.5]

    client, requests, delays = sdk_client([remote_failure] * 4, max_retries=3)
    with pytest.raises(category) as exc:
        client.generate(MESSAGES)
    assert len(requests) == 4 and delays == [0.5, 1, 2]
    assert exc.value.retryable is True


@pytest.mark.parametrize(
    "headers, delay",
    [
        ({"retry-after-ms": "250"}, 0.25),
        ({"retry-after": "8"}, 8),
        ({"retry-after": formatdate(1006, usegmt=True)}, 6),
        ({"retry-after": "0"}, 0),
        ({"retry-after-ms": "nan", "retry-after": "invalid"}, 0.5),
    ],
)
def test_retry_hints_are_validated_and_honored(sdk_client, monkeypatch, headers, delay):
    monkeypatch.setattr("ai.providers.openai.time", lambda: 1000)
    client, requests, delays = sdk_client([failure(429, headers), reply()])
    client.generate(MESSAGES)
    assert len(requests) == 2 and delays == [delay]


@pytest.mark.parametrize(
    "headers", [{"retry-after": "11"}, {"x-should-retry": "false"}]
)
def test_unsafe_or_forbidden_retry_hint_stops(sdk_client, headers):
    client, requests, delays = sdk_client([failure(429, headers)])
    with pytest.raises(LLMRateLimitError):
        client.generate(MESSAGES)
    assert len(requests) == 1 and delays == []


def test_zero_retries_and_unexpected_sdk_error(sdk_client, monkeypatch):
    client, requests, delays = sdk_client([failure(503)], max_retries=0)
    with pytest.raises(LLMProviderError):
        client.generate(MESSAGES)
    assert len(requests) == 1 and delays == []

    def unexpected(**kwargs):
        raise RuntimeError("SECRET provider-specific state")

    monkeypatch.setattr(client._sdk.responses, "create", unexpected)
    with pytest.raises(LLMProviderError, match="failed unexpectedly") as exc:
        client.generate(MESSAGES)
    assert "SECRET" not in str(exc.value)
    assert exc.value.__context__ is None


def test_sdk_initializer_errors_are_sanitized(monkeypatch):
    def invalid_connection(**kwargs):
        raise RuntimeError("SECRET proxy credentials")

    monkeypatch.setattr("ai.providers.openai.OpenAI", invalid_connection)
    with pytest.raises(LLMConfigurationError, match="Could not initialize") as exc:
        OpenAILLMClient(LLMConfig(model="test", api_key="test-only-key"))
    assert "SECRET" not in str(exc.value)
    assert exc.value.__context__ is None
