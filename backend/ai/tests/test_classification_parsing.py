import json

import pytest

from ai.classification.errors import InvalidClassificationOutput
from ai.classification.schemas import MAX_EXPLANATION_LENGTH, parse_classification
from support.models import AnalysisCategory

VALID_JSON = '{"category":"billing","explanation":"The customer reports two charges."}'


@pytest.mark.parametrize("category", AnalysisCategory.values)
def test_accepts_one_object_with_an_exact_category(category):
    text = json.dumps({"category": category, "explanation": "¿Un cobro duplicado?"})
    parsed_category, explanation = parse_classification(f" \n{text}\t")
    assert parsed_category is AnalysisCategory(category)
    assert explanation == "¿Un cobro duplicado?"


def test_accepts_explanation_at_character_limit():
    explanation = "é" * MAX_EXPLANATION_LENGTH
    assert (
        parse_classification(
            json.dumps({"category": "other", "explanation": explanation})
        )[1]
        == explanation
    )


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " \n",
        None,
        123,
        '{"category":',
        "[]",
        "null",
        "42",
        '"billing"',
        f"{VALID_JSON}\n{VALID_JSON}",
        f"Here is the answer: {VALID_JSON}",
        f"{VALID_JSON} Thanks",
        f"```json\n{VALID_JSON}\n```",
        f"[{VALID_JSON}]",
        '{"category":"billing","category":"refund","explanation":"Two labels."}',
        '{"category":"billing","explanation":"First","explanation":"Second"}',
        '{"category":"billing","\\u0063ategory":"billing","explanation":"Repeated key."}',
        pytest.param("[" * 1500 + "0" + "]" * 1500, id="deeply-nested"),
    ],
)
def test_rejects_malformed_or_ambiguous_json(raw):
    with pytest.raises(InvalidClassificationOutput):
        parse_classification(raw)


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"category": "other"},
        {"explanation": "No label."},
        {"category": ["billing", "refund"], "explanation": "Two labels."},
        {"category": 1, "explanation": "Number category."},
        {"category": "refund_status", "explanation": "Waiting for money."},
        {"category": "payments", "explanation": "Billing issue."},
        {"category": "unknown", "explanation": "Invalid key."},
        {"category": "Billing", "explanation": "Wrong case."},
        {"category": " billing ", "explanation": "Padded key."},
        {"category": "other", "explanation": 1},
        {"category": "other", "explanation": None},
        {"category": "other", "explanation": []},
        {"category": "other", "explanation": ""},
        {"category": "other", "explanation": " \t "},
        {"category": "other", "explanation": "Line break\ninside."},
        {"category": "other", "explanation": "Escape \x1b sequence."},
        {"category": "other", "explanation": "x" * (MAX_EXPLANATION_LENGTH + 1)},
        {"category": "other", "explanation": "Unclear issue.", "confidence": 0.7},
    ],
)
def test_rejects_invalid_response_fields(fields):
    with pytest.raises(InvalidClassificationOutput):
        parse_classification(json.dumps(fields))


def test_error_messages_do_not_echo_sensitive_model_output():
    with pytest.raises(InvalidClassificationOutput) as error:
        parse_classification(VALID_JSON + " customer-private-text")
    assert "customer-private-text" not in str(error.value)
    assert error.value.__context__ is None
