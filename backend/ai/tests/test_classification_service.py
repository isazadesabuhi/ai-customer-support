import json

import pytest

from ai.classification.errors import (
    InvalidClassificationInput,
    InvalidClassificationOutput,
)
from ai.classification.service import (
    CLASSIFICATION_OUTPUT_TOKENS,
    CustomerMessageClassifier,
)
from ai.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ai.schemas import LLMResponse, LLMUsage
from ai.testing import FakeLLMClient
from support.models import BODY_MAX_LENGTH, AnalysisCategory
from support.seed_data.scenarios import SCENARIOS

SEED_CASES = {scenario.key: scenario.messages[0][2] for scenario in SCENARIOS}


def fake_result(category, explanation):
    return FakeLLMClient(
        LLMResponse(
            json.dumps({"category": category, "explanation": explanation}),
            "fake",
            "test-model",
            LLMUsage(82, 16, 98),
            "req_fake",
        )
    )


@pytest.mark.parametrize(
    "scenario, category, explanation",
    [
        (
            "shipping-tracking",
            "shipping",
            "The customer asks whether a delayed shipment left the warehouse.",
        ),
        (
            "refund-delay",
            "refund",
            "The customer is waiting for a refund after returning an item.",
        ),
        (
            "billing-duplicate",
            "billing",
            "The customer reports two charges for one order.",
        ),
        (
            "product-keyboard",
            "product",
            "The customer asks about Linux keyboard compatibility.",
        ),
        ("account-lockout", "account", "The customer is blocked by a sign-in loop."),
        ("general-hours", "general", "The customer asks about weekend support hours."),
        (
            "other-cartons",
            "other",
            "The customer asks for empty cartons for a community display.",
        ),
    ],
)
def test_seed_message_yields_expected_result_from_fake_response(
    scenario, category, explanation, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = fake_result(category, explanation)
    text = SEED_CASES[scenario]

    result = CustomerMessageClassifier(client).classify(text)

    assert result.category is AnalysisCategory(category)
    assert result.explanation == explanation
    assert result.prompt_version == "classification-v1"
    assert (result.provider, result.model, result.provider_request_id) == (
        "fake",
        "test-model",
        "req_fake",
    )
    assert result.usage == LLMUsage(82, 16, 98)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.messages[1].content == text
    assert call.model is None and call.temperature is None
    assert call.max_output_tokens == CLASSIFICATION_OUTPUT_TOKENS


@pytest.mark.parametrize(
    "text, category",
    [
        ("  No ha llegado mi paquete. 📦  ", "shipping"),
        ("Je n’arrive pas à me connecter pour télécharger ma facture.", "account"),
        ("キーボードは Linux で使えますか？", "product"),
        ("My parcel was late and the item broke. Please give me a refund.", "refund"),
        ("I am furious that the package still has not arrived.", "shipping"),
        ("Help.", "other"),
        ("Refund?", "refund"),
        ("Something isn't working. Please help.", "other"),
    ],
)
def test_fictional_language_and_intent_cases_keep_user_text(text, category):
    client = fake_result(category, "A short example explanation.")
    result = CustomerMessageClassifier(client).classify(text)
    assert result.category == category
    assert client.calls[0].messages[1].content == text


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        1,
        b"text",
        ["text"],
        "",
        " \t\n",
        pytest.param("\ud800", id="invalid-unicode"),
        pytest.param("é" * (BODY_MAX_LENGTH + 1), id="overlong"),
    ],
)
def test_invalid_input_is_rejected_before_client_call(invalid):
    client = fake_result("other", "Unclear issue.")
    with pytest.raises(InvalidClassificationInput):
        CustomerMessageClassifier(client).classify(invalid)
    assert client.calls == []


def test_accepts_exact_model_length_and_preserves_missing_metadata():
    client = FakeLLMClient(
        LLMResponse(
            '{"category":"other","explanation":"No specific request."}', "fake", None
        )
    )
    text = "é" * BODY_MAX_LENGTH
    result = CustomerMessageClassifier(client, max_output_tokens=96).classify(text)
    assert result.category == AnalysisCategory.OTHER
    assert result.model is result.usage is result.provider_request_id is None
    assert client.calls[0].messages[1].content == text
    assert client.calls[0].max_output_tokens == 96


@pytest.mark.parametrize(
    "error_type",
    [
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMAuthenticationError,
        LLMInvalidRequestError,
        LLMInvalidResponseError,
        LLMProviderError,
        LLMError,
    ],
)
def test_provider_errors_propagate_and_classifier_does_not_retry(error_type):
    error = error_type("Sanitized test provider failure")
    client = FakeLLMClient(error)
    with pytest.raises(error_type) as actual:
        CustomerMessageClassifier(client).classify("Where is my order?")
    assert actual.value is error
    assert len(client.calls) == 1


@pytest.mark.parametrize("body", ["", '{"category":"unknown"}', "Billing seems right."])
def test_invalid_output_raises_without_fallback_or_repair(body):
    client = FakeLLMClient(LLMResponse(body, "fake", "test-model"))
    with pytest.raises(InvalidClassificationOutput):
        CustomerMessageClassifier(client).classify("Where is my order?")
    assert len(client.calls) == 1
