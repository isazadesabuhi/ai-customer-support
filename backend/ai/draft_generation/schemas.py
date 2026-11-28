import re
from dataclasses import dataclass, field
from typing import Literal

from support.models import BODY_MAX_LENGTH

from ..schemas import LLMUsage
from ..structured_output.errors import StructuredOutputError
from ..structured_output.json_parser import parse_json_object
from ..structured_output.validators import require_fields, validate_text_field
from .errors import InvalidDraftGenerationInput, InvalidDraftGenerationOutput

DraftTone = Literal["professional", "friendly", "empathetic"]
DraftLanguage = Literal["en", "fr"]
TONES: tuple[DraftTone, ...] = ("professional", "friendly", "empathetic")
LANGUAGES: tuple[DraftLanguage, ...] = ("en", "fr")

MAX_CONTEXT_LENGTH = 4_000
MAX_DRAFT_LENGTH = 3_000
MAX_INFORMATION_ITEMS = 5
MAX_INFORMATION_LENGTH = 100

_OUTPUT_FIELDS = frozenset({"draft_text", "needs_information", "information_needed"})
_MARKUP = re.compile(r"[<>\x60]|\]\s*\(|\]\s*:")


@dataclass(frozen=True, slots=True)
class DraftGenerationRequest:
    customer_message: str = field(repr=False)
    tone: DraftTone = "professional"
    language: DraftLanguage = "en"
    context: str | None = field(default=None, repr=False)

    def __post_init__(self):
        _validate_input_text(
            self.customer_message, label="Customer message", max_length=BODY_MAX_LENGTH
        )
        if not isinstance(self.tone, str) or self.tone not in TONES:
            raise InvalidDraftGenerationInput(
                "Tone must be professional, friendly, or empathetic."
            )
        if not isinstance(self.language, str) or self.language not in LANGUAGES:
            raise InvalidDraftGenerationInput("Language must be en or fr.")
        if self.context is not None:
            _validate_input_text(
                self.context, label="Context", max_length=MAX_CONTEXT_LENGTH
            )


@dataclass(frozen=True, slots=True)
class DraftGenerationResult:
    draft_text: str = field(repr=False)
    needs_information: bool
    information_needed: tuple[str, ...] = field(repr=False)
    prompt_version: str
    provider: str
    model: str | None
    usage: LLMUsage | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None
    requires_human_review: Literal[True] = field(default=True, init=False)


def _validate_input_text(value: object, *, label: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidDraftGenerationInput(f"{label} must be a nonblank string.")
    if len(value) > max_length:
        raise InvalidDraftGenerationInput(
            f"{label} must contain at most {max_length} characters."
        )
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        pass
    else:
        return
    raise InvalidDraftGenerationInput(f"{label} must contain valid Unicode text.")


def _validate_plain_text(value: object, *, field_name: str, max_length: int) -> str:
    text = validate_text_field(value, field=field_name, max_length=max_length)
    if _MARKUP.search(text):
        raise InvalidDraftGenerationOutput(
            f"{field_name} must be plain text without markup."
        )
    return text


def parse_draft_output(text: str) -> tuple[str, bool, tuple[str, ...]]:
    try:
        payload = parse_json_object(text)
        require_fields(payload, required=_OUTPUT_FIELDS)
        draft_text = _validate_plain_text(
            payload["draft_text"], field_name="draft_text", max_length=MAX_DRAFT_LENGTH
        )
        needs_information = payload["needs_information"]
        if not isinstance(needs_information, bool):
            raise InvalidDraftGenerationOutput(
                "needs_information must be a JSON Boolean."
            )

        items = payload["information_needed"]
        if not isinstance(items, list) or len(items) > MAX_INFORMATION_ITEMS:
            raise InvalidDraftGenerationOutput(
                f"information_needed must be an array of at most {MAX_INFORMATION_ITEMS} items."
            )
        information_needed = tuple(
            _validate_plain_text(
                item,
                field_name="information_needed",
                max_length=MAX_INFORMATION_LENGTH,
            )
            for item in items
        )
    except StructuredOutputError as error:
        message = str(error)
    else:
        if needs_information != bool(information_needed):
            raise InvalidDraftGenerationOutput(
                "needs_information must be true exactly when information_needed has items."
            )
        unique_items = {
            " ".join(item.split()).casefold() for item in information_needed
        }
        if len(unique_items) != len(information_needed):
            raise InvalidDraftGenerationOutput(
                "information_needed must contain distinct items."
            )
        return draft_text, needs_information, information_needed

    raise InvalidDraftGenerationOutput(message)
