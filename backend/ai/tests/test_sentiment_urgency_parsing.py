import json

import pytest

from ai.sentiment_urgency.errors import InvalidSentimentUrgencyOutput
from ai.sentiment_urgency.schemas import MAX_EXPLANATION_LENGTH, parse_sentiment_urgency
from support.models import Sentiment, Urgency

VALID = {
    "sentiment": "neutral",
    "urgency": "normal",
    "sentiment_explanation": "The customer states the facts.",
    "urgency_explanation": "The customer asks for a routine update.",
}
VALID_JSON = json.dumps(VALID)


@pytest.mark.parametrize("sentiment", Sentiment.values)
@pytest.mark.parametrize("urgency", Urgency.values)
def test_supported_labels_are_parsed_independently(sentiment, urgency):
    body = json.dumps(VALID | {"sentiment": sentiment, "urgency": urgency})
    assert parse_sentiment_urgency(f" \n{body}\t") == (
        Sentiment(sentiment),
        Urgency(urgency),
        VALID["sentiment_explanation"],
        VALID["urgency_explanation"],
    )


def test_accepts_explanations_at_character_limit():
    explanation = "é" * MAX_EXPLANATION_LENGTH
    body = json.dumps(
        VALID
        | {"sentiment_explanation": explanation, "urgency_explanation": explanation}
    )
    assert parse_sentiment_urgency(body)[2:] == (explanation, explanation)


@pytest.mark.parametrize("name", list(VALID))
def test_requires_all_four_fields(name):
    body = json.dumps({key: value for key, value in VALID.items() if key != name})
    with pytest.raises(InvalidSentimentUrgencyOutput, match="exactly"):
        parse_sentiment_urgency(body)


@pytest.mark.parametrize("name", ["sentiment", "urgency"])
@pytest.mark.parametrize(
    "invalid", ["unknown", " HIGH ", "Neutral", None, 1, True, ["neutral"]]
)
def test_invalid_labels_never_become_defaults(name, invalid):
    with pytest.raises(InvalidSentimentUrgencyOutput, match=f"unsupported {name}"):
        parse_sentiment_urgency(json.dumps(VALID | {name: invalid}))


@pytest.mark.parametrize("name", ["sentiment", "urgency"])
@pytest.mark.parametrize(
    "invalid",
    [
        "",
        " \t ",
        None,
        1,
        {"summary": "Embedded"},
        "Line break\ninside.",
        "Escape \x1b sequence.",
        pytest.param("x" * (MAX_EXPLANATION_LENGTH + 1), id="overlong"),
    ],
)
def test_explanations_are_individually_validated(name, invalid):
    with pytest.raises(InvalidSentimentUrgencyOutput, match=f"{name} explanation"):
        parse_sentiment_urgency(json.dumps(VALID | {f"{name}_explanation": invalid}))


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " \n",
        None,
        123,
        '{"sentiment":',
        "[]",
        "null",
        '"neutral"',
        f"{VALID_JSON}\n{VALID_JSON}",
        f"Here is the answer: {VALID_JSON}",
        f"{VALID_JSON} Thanks",
        f"```json\n{VALID_JSON}\n```",
        f"[{VALID_JSON}]",
        json.dumps({"result": VALID}),
        json.dumps(VALID | {"confidence": 0.5}),
        pytest.param("[" * 1500 + "0" + "]" * 1500, id="deeply-nested"),
    ],
)
def test_rejects_unexpected_json_shapes(raw):
    with pytest.raises(InvalidSentimentUrgencyOutput):
        parse_sentiment_urgency(raw)


@pytest.mark.parametrize("key", ['"sentiment"', '"\\u0073entiment"'])
def test_rejects_duplicate_json_fields(key):
    body = f'{{{key}:"positive",{VALID_JSON[1:]}'
    with pytest.raises(InvalidSentimentUrgencyOutput, match="duplicate"):
        parse_sentiment_urgency(body)


def test_errors_omit_raw_model_text():
    with pytest.raises(InvalidSentimentUrgencyOutput) as error:
        parse_sentiment_urgency(VALID_JSON + " customer-private-text")
    assert "customer-private-text" not in str(error.value)
    assert error.value.__context__ is None
