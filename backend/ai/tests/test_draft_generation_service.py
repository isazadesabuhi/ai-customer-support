import json
from dataclasses import FrozenInstanceError

import pytest

from ai.draft_generation import (
    CustomerResponseDraftGenerator,
    DraftGenerationRequest,
    DraftGenerationResult,
)
from ai.draft_generation.errors import InvalidDraftGenerationInput
from ai.draft_generation.schemas import MAX_CONTEXT_LENGTH
from ai.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ai.schemas import LLMResponse, LLMUsage
from ai.testing import FakeLLMClient
from support.models import BODY_MAX_LENGTH

_MESSAGE = " Où est ma commande ? "
_CONTEXT = " Policy excerpt for this fictional test.\nVerified status: Shipped. "


@pytest.fixture
def provider_response():
    return LLMResponse(
        text=json.dumps(
            {
                "draft_text": "Could you share your order reference?",
                "needs_information": True,
                "information_needed": ["order reference"],
            }
        ),
        provider="fake",
        model="test-model",
        usage=LLMUsage(input_tokens=10, output_tokens=15, total_tokens=25),
        provider_request_id="req-fictional",
        finish_reason="completed",
    )


@pytest.mark.parametrize(
    "message",
    [_MESSAGE, "配送状況を教えてください。", "🙂" * BODY_MAX_LENGTH],
    ids=["french", "japanese", "maximum-length"],
)
def test_preserve_original_input(message, provider_response):
    client = FakeLLMClient(provider_response)
    request = DraftGenerationRequest(message, context=_CONTEXT)
    CustomerResponseDraftGenerator(client).generate(request)
    data = json.loads(client.calls[0].messages[1].content)
    assert data["customer_message"] == message
    assert data["verified_business_context"] == _CONTEXT
    assert (data["language"], data["tone"]) == ("en", "professional")


@pytest.mark.parametrize(
    "changes",
    [
        {"customer_message": ""},
        {"customer_message": " \n\t"},
        {"customer_message": None},
        {"customer_message": 1},
        {"customer_message": "x" * (BODY_MAX_LENGTH + 1)},
        {"customer_message": "\ud800"},
        {"context": 12},
        {"context": ""},
        {"context": " \t"},
        {"context": "x" * (MAX_CONTEXT_LENGTH + 1)},
        {"context": "\ud800"},
        {"tone": None},
        {"tone": ["friendly"]},
        {"tone": "promise a refund"},
        {"tone": "Professional"},
        {"language": None},
        {"language": 1},
        {"language": "de"},
        {"language": "FR"},
    ],
)
def test_invalid_request(changes):
    with pytest.raises(InvalidDraftGenerationInput) as caught:
        DraftGenerationRequest(**({"customer_message": _MESSAGE} | changes))
    for value in changes.values():
        if isinstance(value, str) and len(value.strip()) > 20:
            assert value not in str(caught.value)


def test_context_at_limit():
    context = "é" * MAX_CONTEXT_LENGTH
    assert DraftGenerationRequest(_MESSAGE, context=context).context == context


def test_untyped_request_is_rejected_before_provider(provider_response):
    client = FakeLLMClient(provider_response)
    with pytest.raises(InvalidDraftGenerationInput, match="DraftGenerationRequest"):
        CustomerResponseDraftGenerator(client).generate(_MESSAGE)
    assert client.calls == []


@pytest.mark.parametrize("budget", [True, 15, 501, "500", None])
def test_invalid_output_budget(budget, provider_response):
    client = FakeLLMClient(provider_response)
    with pytest.raises(
        InvalidDraftGenerationInput, match="Output tokens|output tokens"
    ):
        CustomerResponseDraftGenerator(client, max_output_tokens=budget)
    assert client.calls == []


@pytest.mark.parametrize("budget", [None, 128, 16])
def test_typed_draft_review_and_metadata(budget, provider_response, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeLLMClient(provider_response)
    options = {} if budget is None else {"max_output_tokens": budget}
    result = CustomerResponseDraftGenerator(client, **options).generate(
        DraftGenerationRequest(_MESSAGE)
    )

    assert isinstance(result, DraftGenerationResult)
    assert result.draft_text == "Could you share your order reference?"
    assert result.needs_information is True
    assert result.information_needed == ("order reference",)
    assert result.requires_human_review is True
    assert result.prompt_version == "draft-generation-v1"
    assert result.provider == provider_response.provider
    assert result.model == provider_response.model
    assert result.usage == provider_response.usage
    assert result.provider_request_id == provider_response.provider_request_id
    assert result.finish_reason == provider_response.finish_reason
    assert result.draft_text not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.requires_human_review = False

    [call] = client.calls
    assert call.max_output_tokens == (500 if budget is None else budget)
    assert call.temperature is None
    assert call.model is None


def test_absent_provider_metadata():
    client = FakeLLMClient(
        LLMResponse(
            text='{"draft_text":"Merci !","needs_information":false,"information_needed":[]}',
            provider="fake",
            model=None,
        )
    )
    result = CustomerResponseDraftGenerator(client).generate(
        DraftGenerationRequest(_MESSAGE, language="fr")
    )
    assert result.model is result.usage is result.provider_request_id is None
    assert result.finish_reason is None
    assert result.needs_information is False
    assert result.information_needed == ()
    assert result.requires_human_review is True


@pytest.mark.parametrize(
    "error_type",
    [
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMInvalidRequestError,
        LLMProviderError,
        LLMInvalidResponseError,
    ],
)
def test_provider_errors_are_preserved_without_extra_retry(error_type):
    error = error_type("Sanitized provider error.", retryable=True)
    client = FakeLLMClient(error)
    with pytest.raises(error_type) as caught:
        CustomerResponseDraftGenerator(client).generate(
            DraftGenerationRequest(_MESSAGE)
        )
    assert caught.value is error
    assert len(client.calls) == 1
