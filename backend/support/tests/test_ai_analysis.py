import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from support.models import (
    AIAnalysis,
    AnalysisCategory,
    MessageSender,
    Sentiment,
    Urgency,
)

from . import postgres_model_tests

pytestmark = postgres_model_tests


def analysis_for(message, **overrides):
    values = {
        "message": message,
        "category": AnalysisCategory.SHIPPING,
        "sentiment": Sentiment.NEUTRAL,
        "urgency": Urgency.NORMAL,
        "model_name": "example/model",
        **overrides,
    }
    return AIAnalysis(**values)


@pytest.mark.parametrize("confidence", [None, 0.0, 0.5, 1.0])
def test_analysis_accepts_optional_confidence_and_links_to_message(message, confidence):
    analysis = analysis_for(message, confidence=confidence)
    analysis.full_clean()
    analysis.save()
    analysis.refresh_from_db()

    assert message.ai_analysis == analysis
    assert analysis.confidence == confidence
    assert analysis.reason == ""
    assert timezone.is_aware(analysis.created_at)
    assert str(analysis) == f"shipping analysis for message {message.pk}"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "invalid"),
        ("sentiment", "invalid"),
        ("urgency", "now"),
        ("model_name", " \t "),
        ("confidence", -0.1),
        ("confidence", 1.1),
        ("confidence", float("nan")),
        ("confidence", float("inf")),
        ("confidence", float("-inf")),
    ],
)
def test_analysis_rejects_invalid_values(message, field, value):
    with pytest.raises(ValidationError) as error:
        analysis_for(message, **{field: value}).full_clean()

    assert field in error.value.message_dict


@pytest.mark.parametrize("sender", [MessageSender.AGENT, MessageSender.SYSTEM])
def test_analysis_requires_customer_authored_message(message, sender):
    message.sender = sender
    message.save(update_fields=["sender"])

    with pytest.raises(ValidationError) as error:
        analysis_for(message).full_clean()

    assert "message" in error.value.message_dict


def test_message_deletion_cascades_to_analysis(message):
    analysis = analysis_for(message)
    analysis.save()

    message.delete()

    assert not AIAnalysis.objects.filter(pk=analysis.pk).exists()
