import json

import pytest

from ai.structured_output.errors import InvalidJSONOutput
from ai.structured_output.json_parser import (
    MAX_JSON_DEPTH,
    MAX_JSON_LENGTH,
    parse_json_object,
)


def test_accepts_one_object_and_preserves_unicode_and_json_values():
    data = {
        "message": "届きません。 📦 ¿Dónde está?",
        "values": [True, 4, 0.25, None, {"ok": False}],
    }
    assert parse_json_object(f" \n{json.dumps(data, ensure_ascii=False)}\r\n") == data
    assert parse_json_object("{}") == {}


@pytest.mark.parametrize("value", [None, 12, b"{}", {}, "", " \t\n"])
def test_rejects_non_string_or_blank(value):
    with pytest.raises(InvalidJSONOutput) as error:
        parse_json_object(value)
    assert error.value.code == "nonblank"


@pytest.mark.parametrize(
    "text",
    [
        "{category: billing}",
        '{"field":}',
        '{"field":1,}',
        '{"field":"raw\x00control"}',
        "[]",
        '"value"',
        "2",
        "true",
        "false",
        "null",
        "{} {}",
        "Here is the result: {}",
        "{} trailing text",
        "```json\n{}\n```",
    ],
)
def test_rejects_malformed_or_wrapped_documents(text):
    with pytest.raises(InvalidJSONOutput) as error:
        parse_json_object(text)
    assert error.value.code == "invalid"
    assert error.value.__context__ is None


@pytest.mark.parametrize(
    "text",
    [
        '{"label":"a","label":"b"}',
        '{"label":0,"\\u006cabel":1}',
        '{"outer":{"label":"a","label":"b"}}',
        '{"items":[{"label":1,"label":2}]}',
    ],
)
def test_rejects_duplicate_keys_at_every_depth(text):
    with pytest.raises(InvalidJSONOutput, match="duplicate") as error:
        parse_json_object(text)
    assert error.value.code == "duplicate"


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
def test_rejects_nonstandard_and_nonfinite_numbers_at_all_levels(number):
    with pytest.raises(InvalidJSONOutput, match="finite") as error:
        parse_json_object(f'{{"nested":[{number}]}}')
    assert error.value.code == "nonfinite"
    assert parse_json_object('{"text":"NaN Infinity"}') == {"text": "NaN Infinity"}


def test_size_limit_applies_to_original_document_in_characters():
    value = '{"text":"é"}'
    within_limit = value + " " * (MAX_JSON_LENGTH - len(value))
    assert parse_json_object(within_limit) == {"text": "é"}
    with pytest.raises(
        InvalidJSONOutput, match=f"{MAX_JSON_LENGTH} characters"
    ) as error:
        parse_json_object(within_limit + " ")
    assert error.value.code == "size"


def test_container_depth_counts_root_object_and_nested_arrays_and_objects():
    arrays = "[" * (MAX_JSON_DEPTH - 2) + '{"value":0}' + "]" * (MAX_JSON_DEPTH - 2)
    assert parse_json_object(f'{{"items":{arrays}}}')["items"]
    with pytest.raises(InvalidJSONOutput, match="nested too deeply") as error:
        parse_json_object(f'{{"items":[{arrays}]}}')
    assert error.value.code == "nesting"


def test_decoder_recursion_is_sanitized():
    text = '{"data":' + "[" * 1200 + "0" + "]" * 1200 + "}"
    with pytest.raises(InvalidJSONOutput, match="nested too deeply") as error:
        parse_json_object(text)
    assert error.value.code == "nesting"
    assert error.value.__context__ is None


def test_error_strings_do_not_include_unsafe_keys_or_document():
    for text in (
        '{"Authorization: Bearer synthetic-secret":1,"Authorization: Bearer synthetic-secret":2}',
        '{"customer-private-text":',
    ):
        with pytest.raises(InvalidJSONOutput) as error:
            parse_json_object(text)
        assert "synthetic-secret" not in str(error.value)
        assert "Authorization" not in str(error.value)
        assert "customer-private-text" not in str(error.value)
