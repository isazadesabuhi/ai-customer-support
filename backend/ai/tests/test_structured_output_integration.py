import json
from dataclasses import asdict

import pytest

from ai.classification.errors import InvalidClassificationOutput
from ai.classification.service import CustomerMessageClassifier
from ai.schemas import LLMResponse, LLMUsage
from ai.sentiment_urgency.errors import InvalidSentimentUrgencyOutput
from ai.sentiment_urgency.service import SentimentUrgencyAnalyzer
from ai.structured_output.json_parser import MAX_JSON_LENGTH
from ai.testing import FakeLLMClient


@pytest.fixture(params=["classification", "sentiment_urgency"])
def contract(request):
    if request.param == "classification":
        return (
            CustomerMessageClassifier,
            "classify",
            InvalidClassificationOutput,
            "classification-v1",
            256,
            {"category": "billing", "explanation": "The customer reports two charges."},
        )
    return (
        SentimentUrgencyAnalyzer,
        "analyze",
        InvalidSentimentUrgencyOutput,
        "sentiment-urgency-v1",
        384,
        {
            "sentiment": "neutral",
            "urgency": "normal",
            "sentiment_explanation": "The wording is factual.",
            "urgency_explanation": "The customer describes a routine issue.",
        },
    )


def test_refactor_preserves_service_result_metadata_and_one_call(contract, monkeypatch):
    factory, method, _, version, limit, fields = contract
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    usage = LLMUsage(18, 12, 30)
    fake = FakeLLMClient(
        LLMResponse(json.dumps(fields), "fake", "test-model", usage, "request-test")
    )
    message = "  I see two charges on my statement.  "

    result = getattr(factory(fake), method)(message)

    assert asdict(result) == fields | {
        "provider": "fake",
        "model": "test-model",
        "prompt_version": version,
        "usage": asdict(usage),
        "provider_request_id": "request-test",
    }
    assert len(fake.calls) == 1
    request = fake.calls[0]
    assert request.max_output_tokens == limit
    assert request.model is request.temperature is None
    instructions, customer = request.messages
    assert instructions.role == "developer" and message not in instructions.content
    assert (customer.role, customer.content) == ("user", message)


@pytest.mark.parametrize(
    "kind, description",
    [
        ("malformed", "single JSON object"),
        ("duplicate", "duplicate field"),
        ("extra-key", "requires exactly"),
        ("oversized", "single JSON object"),
        ("nonfinite", "single JSON object"),
    ],
)
def test_shared_failures_stay_typed_sanitized_and_single_call(
    contract, kind, description, caplog
):
    factory, method, public_error, _, _, fields = contract
    output = json.dumps(fields)
    private = "Authorization: Bearer synthetic-test-secret"
    customer = "private customer text for error test"
    if kind == "malformed":
        output += private
    elif kind == "duplicate":
        first = next(iter(fields))
        output = output[:-1] + f', "{first}": {json.dumps(private)}}}'
    elif kind == "extra-key":
        output = json.dumps(fields | {private: customer})
    elif kind == "oversized":
        output += " " * MAX_JSON_LENGTH
    else:
        output = json.dumps(fields | {next(iter(fields)): float("nan")})

    fake = FakeLLMClient(LLMResponse(output, "fake", None))
    with pytest.raises(public_error, match=description) as error:
        getattr(factory(fake), method)(customer)

    assert len(fake.calls) == 1
    assert error.value.__context__ is None
    for sensitive in (private, customer, "synthetic-test-secret", output[:24]):
        assert sensitive not in str(error.value)
        assert sensitive not in caplog.text
