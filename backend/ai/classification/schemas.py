from dataclasses import dataclass, field

from support.models import AnalysisCategory

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
from .errors import InvalidClassificationOutput

MAX_EXPLANATION_LENGTH = 300
_OUTPUT_FIELDS = frozenset({"category", "explanation"})


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    category: AnalysisCategory
    explanation: str = field(repr=False)
    prompt_version: str
    provider: str
    model: str | None
    usage: LLMUsage | None = None
    provider_request_id: str | None = None


def parse_classification(text: str) -> tuple[AnalysisCategory, str]:
    try:
        payload = parse_json_object(text)
        require_fields(payload, required=_OUTPUT_FIELDS)
        category = validate_enum(
            payload["category"], allowed=AnalysisCategory.values, field="category"
        )
        explanation = validate_text_field(
            payload["explanation"],
            field="explanation",
            max_length=MAX_EXPLANATION_LENGTH,
        )
        return AnalysisCategory(category), explanation
    except InvalidJSONOutput as error:
        message = {
            "nonblank": "Classification requires a nonblank JSON response.",
            "duplicate": "Classification JSON has a duplicate field.",
        }.get(error.code, "Classification output must be a single JSON object.")
    except InvalidOutputShape:
        message = "Classification requires exactly category and explanation fields."
    except InvalidOutputField as error:
        message = (
            "Classification returned an unsupported category."
            if error.field == "category"
            else f"Classification requires a nonblank, printable explanation of at most {MAX_EXPLANATION_LENGTH} characters."
        )

    raise InvalidClassificationOutput(message)
