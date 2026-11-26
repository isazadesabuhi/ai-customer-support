import json
from dataclasses import dataclass, field

from support.models import Sentiment, Urgency

from ..schemas import LLMUsage
from .errors import InvalidSentimentUrgencyOutput

MAX_EXPLANATION_LENGTH = 300
_OUTPUT_FIELDS = {
    "sentiment",
    "urgency",
    "sentiment_explanation",
    "urgency_explanation",
}


@dataclass(frozen=True, slots=True)
class SentimentUrgencyResult:
    sentiment: Sentiment
    urgency: Urgency
    sentiment_explanation: str = field(repr=False)
    urgency_explanation: str = field(repr=False)
    prompt_version: str
    provider: str
    model: str | None
    usage: LLMUsage | None = None
    provider_request_id: str | None = None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, value in pairs:
        if name in fields:
            raise InvalidSentimentUrgencyOutput("Analysis JSON has a duplicate field.")
        fields[name] = value
    return fields


def _explanation(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isprintable()
        or len(value) > MAX_EXPLANATION_LENGTH
    ):
        raise InvalidSentimentUrgencyOutput(
            f"The {name} explanation must be nonblank printable text of at most {MAX_EXPLANATION_LENGTH} characters."
        )
    return value


def parse_sentiment_urgency(text: str) -> tuple[Sentiment, Urgency, str, str]:
    if not isinstance(text, str) or not text.strip():
        raise InvalidSentimentUrgencyOutput(
            "Analysis requires a nonblank JSON response."
        )

    try:
        payload = json.loads(text, object_pairs_hook=_unique_fields)
    except (ValueError, RecursionError):
        payload = None

    if not isinstance(payload, dict):
        raise InvalidSentimentUrgencyOutput(
            "Analysis output must be a single JSON object."
        )
    if set(payload) != _OUTPUT_FIELDS:
        raise InvalidSentimentUrgencyOutput(
            "Analysis requires exactly sentiment, urgency, and their two explanation fields."
        )

    sentiment = payload["sentiment"]
    urgency = payload["urgency"]
    if not isinstance(sentiment, str) or sentiment not in Sentiment.values:
        raise InvalidSentimentUrgencyOutput(
            "Analysis returned an unsupported sentiment."
        )
    if not isinstance(urgency, str) or urgency not in Urgency.values:
        raise InvalidSentimentUrgencyOutput("Analysis returned an unsupported urgency.")

    return (
        Sentiment(sentiment),
        Urgency(urgency),
        _explanation(payload["sentiment_explanation"], "sentiment"),
        _explanation(payload["urgency_explanation"], "urgency"),
    )
