import json
from dataclasses import dataclass, field

from support.models import AnalysisCategory

from ..schemas import LLMUsage
from .errors import InvalidClassificationOutput

MAX_EXPLANATION_LENGTH = 300


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    category: AnalysisCategory
    explanation: str = field(repr=False)
    prompt_version: str
    provider: str
    model: str | None
    usage: LLMUsage | None = None
    provider_request_id: str | None = None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, value in pairs:
        if name in fields:
            raise InvalidClassificationOutput(
                "Classification JSON has a duplicate field."
            )
        fields[name] = value
    return fields


def parse_classification(text: str) -> tuple[AnalysisCategory, str]:
    if not isinstance(text, str) or not text.strip():
        raise InvalidClassificationOutput(
            "Classification requires a nonblank JSON response."
        )

    try:
        payload = json.loads(text, object_pairs_hook=_unique_fields)
    except (ValueError, RecursionError):
        payload = None

    if not isinstance(payload, dict):
        raise InvalidClassificationOutput(
            "Classification output must be a single JSON object."
        )
    if set(payload) != {"category", "explanation"}:
        raise InvalidClassificationOutput(
            "Classification requires exactly category and explanation fields."
        )

    category = payload["category"]
    if not isinstance(category, str) or category not in AnalysisCategory.values:
        raise InvalidClassificationOutput(
            "Classification returned an unsupported category."
        )

    explanation = payload["explanation"]
    if (
        not isinstance(explanation, str)
        or not explanation.strip()
        or not explanation.isprintable()
        or len(explanation) > MAX_EXPLANATION_LENGTH
    ):
        raise InvalidClassificationOutput(
            f"Classification requires a nonblank, printable explanation of at most {MAX_EXPLANATION_LENGTH} characters."
        )
    return AnalysisCategory(category), explanation
