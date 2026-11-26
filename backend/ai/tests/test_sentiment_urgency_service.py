import json

import pytest

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
from ai.sentiment_urgency.errors import (
    InvalidSentimentUrgencyInput,
    InvalidSentimentUrgencyOutput,
)
from ai.sentiment_urgency.service import (
    ANALYSIS_OUTPUT_TOKENS,
    SentimentUrgencyAnalyzer,
)
from ai.testing import FakeLLMClient
from support.models import BODY_MAX_LENGTH, Sentiment, Urgency
from support.seed_data.scenarios import SCENARIOS

SEED_TEXT = {scenario.key: scenario.messages[0][2] for scenario in SCENARIOS}


def fake_result(sentiment, urgency):
    return FakeLLMClient(
        LLMResponse(
            json.dumps(
                {
                    "sentiment": sentiment,
                    "urgency": urgency,
                    "sentiment_explanation": "Example wording for the sentiment decision.",
                    "urgency_explanation": "Example supporting circumstances for urgency.",
                }
            ),
            "fake",
            "test-model",
            LLMUsage(90, 25, 115),
            "req_fake",
        )
    )


@pytest.mark.parametrize(
    "scenario, sentiment, urgency",
    [
        ("shipping-tracking", "neutral", "high"),
        ("refund-delay", "negative", "normal"),
        ("account-lockout", "neutral", "high"),
        ("product-keyboard", "neutral", "low"),
        ("general-hours", "positive", "low"),
        ("billing-discount", "neutral", "normal"),
        ("refund-return", "neutral", "normal"),
        ("product-headset", "neutral", "low"),
    ],
)
def test_seed_messages_use_only_the_selected_text(
    scenario, sentiment, urgency, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake = fake_result(sentiment, urgency)
    message = SEED_TEXT[scenario]

    result = SentimentUrgencyAnalyzer(fake).analyze(message)

    assert result.sentiment is Sentiment(sentiment)
    assert result.urgency is Urgency(urgency)
    assert result.sentiment_explanation == "Example wording for the sentiment decision."
    assert result.urgency_explanation == "Example supporting circumstances for urgency."
    assert result.prompt_version == "sentiment-urgency-v1"
    assert (result.provider, result.model, result.provider_request_id) == (
        "fake",
        "test-model",
        "req_fake",
    )
    assert result.usage == LLMUsage(90, 25, 115)
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert len(call.messages) == 2 and call.messages[1].content == message
    assert call.model is None and call.temperature is None
    assert call.max_output_tokens == ANALYSIS_OUTPUT_TOKENS


@pytest.mark.parametrize(
    "text, sentiment, urgency",
    [
        ("Thank you for the excellent service!", "positive", "low"),
        (
            "Your team has been excellent. Could you confirm the replacement today? I need it for tomorrow's event.",
            "positive",
            "high",
        ),
        ("My order is two days late. Can you check its status?", "neutral", "normal"),
        (
            "My account is locked, and I need the invoice before the finance desk closes in one hour.",
            "neutral",
            "high",
        ),
        (
            "I'm disappointed the blue mouse is unavailable. I planned to buy it next month.",
            "negative",
            "low",
        ),
        (
            "I'm frustrated that my refund is taking so long. Can you provide an update?",
            "negative",
            "normal",
        ),
        (
            "I'm upset about the replacement delay. I need it for tonight's event.",
            "negative",
            "high",
        ),
        (
            "URGENT!!! Are you releasing the keyboard in another color next year?",
            "neutral",
            "low",
        ),
        ("  Merci, votre aide était excellente ! 📦  ", "positive", "low"),
        ("Necesito el cargador antes del evento de mañana.", "neutral", "high"),
        ("Can someone help me?", "neutral", "normal"),
    ],
)
def test_fictional_cases_preserve_independent_fake_labels(text, sentiment, urgency):
    fake = fake_result(sentiment, urgency)
    result = SentimentUrgencyAnalyzer(fake).analyze(text)
    assert (result.sentiment, result.urgency) == (sentiment, urgency)
    assert len(fake.calls) == 1 and fake.calls[0].messages[1].content == text


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
def test_invalid_input_fails_before_calling_the_client(invalid):
    fake = fake_result("neutral", "normal")
    with pytest.raises(InvalidSentimentUrgencyInput):
        SentimentUrgencyAnalyzer(fake).analyze(invalid)
    assert fake.calls == []


def test_accepts_character_limit_and_preserves_missing_metadata():
    fake = FakeLLMClient(
        LLMResponse(
            '{"sentiment":"neutral","urgency":"normal","sentiment_explanation":"No clear tone.",'
            '"urgency_explanation":"Routine issue."}',
            "fake",
            None,
        )
    )
    text = "é" * BODY_MAX_LENGTH
    result = SentimentUrgencyAnalyzer(fake, max_output_tokens=192).analyze(text)
    assert result.model is result.usage is result.provider_request_id is None
    assert len(fake.calls) == 1
    assert (
        fake.calls[0].messages[1].content == text
        and fake.calls[0].max_output_tokens == 192
    )


@pytest.mark.parametrize(
    "error_type",
    [
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMInvalidRequestError,
        LLMInvalidResponseError,
        LLMProviderError,
        LLMError,
    ],
)
def test_provider_failure_propagates_without_analysis_retries(error_type):
    failure = error_type("Sanitized fixture failure", retryable=True)
    fake = FakeLLMClient(failure)
    with pytest.raises(error_type) as received:
        SentimentUrgencyAnalyzer(fake).analyze("I need the item before tomorrow.")
    assert received.value is failure
    assert len(fake.calls) == 1


@pytest.mark.parametrize(
    "text", ["", '{"sentiment":"unknown"}', "The urgency appears high."]
)
def test_invalid_response_raises_without_repair_or_defaults(text):
    fake = FakeLLMClient(LLMResponse(text, "fake", "test-model"))
    with pytest.raises(InvalidSentimentUrgencyOutput):
        SentimentUrgencyAnalyzer(fake).analyze("I need the item before tomorrow.")
    assert len(fake.calls) == 1
