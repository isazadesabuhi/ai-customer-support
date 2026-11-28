import json

import pytest

from ai.draft_generation import CustomerResponseDraftGenerator, DraftGenerationRequest
from ai.draft_generation.errors import InvalidDraftGenerationOutput
from ai.draft_generation.schemas import (
    MAX_DRAFT_LENGTH,
    MAX_INFORMATION_ITEMS,
    MAX_INFORMATION_LENGTH,
    parse_draft_output,
)
from ai.schemas import LLMResponse
from ai.testing import FakeLLMClient

_VALID = {
    "draft_text": " Bonjour, quel est le numéro de commande ? ",
    "needs_information": True,
    "information_needed": [" numéro de commande "],
}


def test_valid_draft_at_length_and_count_limits():
    draft = "é" * MAX_DRAFT_LENGTH
    items = tuple(
        str(index) * MAX_INFORMATION_LENGTH for index in range(MAX_INFORMATION_ITEMS)
    )
    output = _VALID | {"draft_text": draft, "information_needed": items}
    assert parse_draft_output(json.dumps(output, ensure_ascii=False)) == (
        draft,
        True,
        items,
    )


def test_valid_draft_preserves_visible_text():
    assert parse_draft_output(json.dumps(_VALID)) == (
        _VALID["draft_text"],
        True,
        tuple(_VALID["information_needed"]),
    )


@pytest.mark.parametrize("missing", _VALID)
def test_missing_required_field(missing):
    output = {key: value for key, value in _VALID.items() if key != missing}
    with pytest.raises(InvalidDraftGenerationOutput, match="missing required"):
        parse_draft_output(json.dumps(output))


@pytest.mark.parametrize(
    "changes",
    [
        {"draft_text": ""},
        {"draft_text": "   "},
        {"draft_text": 3},
        {"draft_text": ["draft"]},
        {"draft_text": "a" * (MAX_DRAFT_LENGTH + 1)},
        {"draft_text": "Hello\nSecond line"},
        {"draft_text": "<script>alert(1)</script>"},
        {"draft_text": "[here](javascript:alert(1))"},
        {"draft_text": "[here]: javascript:alert(1)"},
        {"draft_text": "\x60sample code\x60"},
        {"needs_information": "true"},
        {"needs_information": "false"},
        {"needs_information": 1},
        {"needs_information": None},
        {"information_needed": "reference"},
        {"information_needed": {}},
        {"information_needed": [None]},
        {"information_needed": [[]]},
        {"information_needed": [True]},
        {"information_needed": [""]},
        {"information_needed": ["   "]},
        {"information_needed": ["a" * (MAX_INFORMATION_LENGTH + 1)]},
        {"information_needed": ["reference\t"]},
        {"information_needed": ["<img src=x onerror=alert(1)>"]},
        {
            "information_needed": [
                str(index) for index in range(MAX_INFORMATION_ITEMS + 1)
            ]
        },
        {"requires_human_review": False},
        {"approval_status": "approved"},
    ],
)
def test_invalid_field_types_lengths_and_markup(changes):
    with pytest.raises(InvalidDraftGenerationOutput):
        parse_draft_output(json.dumps(_VALID | changes))


@pytest.mark.parametrize(("needs_info", "items"), [(False, ["reference"]), (True, [])])
def test_contradictory_information_fields(needs_info, items):
    output = _VALID | {"needs_information": needs_info, "information_needed": items}
    with pytest.raises(InvalidDraftGenerationOutput, match="must be true exactly when"):
        parse_draft_output(json.dumps(output))


@pytest.mark.parametrize(
    "items", [["order reference"] * 2, ["Order  Reference", " order reference "]]
)
def test_duplicate_information_items(items):
    with pytest.raises(InvalidDraftGenerationOutput, match="distinct"):
        parse_draft_output(json.dumps(_VALID | {"information_needed": items}))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "{",
        "[]",
        "{} {}",
        'Draft: {"draft_text":"example"}',
        "\x60\x60\x60json\n{}\n\x60\x60\x60",
        '{"draft_text":"One","draft_text":"Two","needs_information":false,"information_needed":[]}',
        '{"draft_text":"ok","needs_information":NaN,"information_needed":[]}',
    ],
)
def test_invalid_provider_document_is_sanitized_and_never_retried(text):
    client = FakeLLMClient(LLMResponse(text=text, provider="fake", model=None))
    with pytest.raises(InvalidDraftGenerationOutput) as caught:
        CustomerResponseDraftGenerator(client).generate(DraftGenerationRequest("Hello"))
    assert caught.value.__context__ is None
    assert len(client.calls) == 1


def test_error_does_not_repeat_printable_draft_customer_text_or_unexpected_keys():
    private_draft = "Authorization: Bearer fake-secret-for-test"
    private_message = "Private sample customer message"
    unexpected_key = "sensitive-unknown-field"
    output = _VALID | {"draft_text": private_draft, unexpected_key: private_message}
    client = FakeLLMClient(
        LLMResponse(text=json.dumps(output), provider="fake", model=None)
    )
    with pytest.raises(InvalidDraftGenerationOutput) as caught:
        CustomerResponseDraftGenerator(client).generate(
            DraftGenerationRequest(private_message)
        )
    for sensitive in (private_draft, private_message, unexpected_key):
        assert sensitive not in str(caught.value)
