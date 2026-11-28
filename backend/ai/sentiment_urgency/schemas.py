from dataclasses import dataclass, field

from support.models import Sentiment, Urgency

from ..schemas import LLMUsage
from ..structured_output.errors import (
    InvalidJSONOutput,
    InvalidOutputField,
    InvalidOutputShape,
)
from ..structured_output.json_parser import parse_json_object
from ..structured_output.validators import (
    require_fields,
    validate_enum,
    validate_text_field,
)
from .errors import InvalidSentimentUrgencyOutput

MAX_EXPLANATION_LENGTH = 300
_OUTPUT_FIELDS = frozenset(
    {
        "sentiment",
        "urgency",
        "sentiment_explanation",
        "urgency_explanation",
    }
)


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


def parse_sentiment_urgency(text: str) -> tuple[Sentiment, Urgency, str, str]:
    try:
        payload = parse_json_object(text)
        require_fields(payload, required=_OUTPUT_FIELDS)
        sentiment = validate_enum(
            payload["sentiment"], allowed=Sentiment.values, field="sentiment"
        )
        urgency = validate_enum(
            payload["urgency"], allowed=Urgency.values, field="urgency"
        )
        sentiment_explanation = validate_text_field(
            payload["sentiment_explanation"],
            field="sentiment_explanation",
            max_length=MAX_EXPLANATION_LENGTH,
        )
        urgency_explanation = validate_text_field(
            payload["urgency_explanation"],
            field="urgency_explanation",
            max_length=MAX_EXPLANATION_LENGTH,
        )
        return (
            Sentiment(sentiment),
            Urgency(urgency),
            sentiment_explanation,
            urgency_explanation,
        )
    except InvalidJSONOutput as error:
        message = {
            "nonblank": "Analysis requires a nonblank JSON response.",
            "duplicate": "Analysis JSON has a duplicate field.",
        }.get(error.code, "Analysis output must be a single JSON object.")
    except InvalidOutputShape:
        message = "Analysis requires exactly sentiment, urgency, and their two explanation fields."
    except InvalidOutputField as error:
        if error.field in {"sentiment", "urgency"}:
            message = f"Analysis returned an unsupported {error.field}."
        else:
            name = error.field.removesuffix("_explanation")
            message = f"The {name} explanation must be nonblank printable text of at most {MAX_EXPLANATION_LENGTH} characters."

    raise InvalidSentimentUrgencyOutput(message)
