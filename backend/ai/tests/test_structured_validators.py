import pytest

from ai.structured_output.errors import InvalidOutputField, InvalidOutputShape
from ai.structured_output.validators import (
    require_fields,
    validate_enum,
    validate_text_field,
)
from support.models import AnalysisCategory

REQUIRED = frozenset({"category", "explanation"})


def test_required_fields_and_opt_in_optional_fields_preserve_input():
    data = {"category": "billing", "explanation": "Duplicate charge."}
    before = data.copy()
    require_fields(data, required=REQUIRED)
    require_fields(data, required=REQUIRED, allowed=REQUIRED | {"optional"})
    assert data == before
    extended = data | {"optional": None}
    require_fields(extended, required=REQUIRED, allowed=REQUIRED | {"optional"})
    assert extended == before | {"optional": None}


@pytest.mark.parametrize(
    "data, missing, extra",
    [
        ({"category": "billing"}, 1, 0),
        ({}, 2, 0),
        (
            {
                "category": "billing",
                "explanation": "Duplicate charge.",
                "private-extra": 1,
            },
            0,
            1,
        ),
        ({"first-private-extra": 1, "second-private-extra": 2}, 2, 2),
    ],
)
def test_shape_reports_counts_without_echoing_data_or_mutating_it(data, missing, extra):
    before = data.copy()
    with pytest.raises(InvalidOutputShape) as error:
        require_fields(data, required=REQUIRED)
    assert f"{missing} missing" in str(error.value) and f"{extra} unexpected" in str(
        error.value
    )
    assert "private-extra" not in str(error.value) and "Duplicate charge" not in str(
        error.value
    )
    assert data == before


def test_rejects_inconsistent_fields_and_non_object():
    with pytest.raises(
        InvalidOutputShape, match="Required fields must also be allowed"
    ):
        require_fields({}, required=REQUIRED, allowed=frozenset({"category"}))
    with pytest.raises(InvalidOutputShape, match="require a JSON object"):
        require_fields([], required=REQUIRED)


@pytest.mark.parametrize(
    "allowed", [AnalysisCategory, AnalysisCategory.values, frozenset({"refund"})]
)
def test_enum_accepts_django_choices_or_plain_strings(allowed):
    assert validate_enum("refund", allowed=allowed, field="category") == "refund"


@pytest.mark.parametrize(
    "value",
    [
        "refund_status",
        "Refund",
        " refund ",
        "",
        1,
        None,
        True,
        ["refund"],
        "private-label",
    ],
)
def test_enum_rejects_unsupported_values_exactly(value):
    with pytest.raises(InvalidOutputField) as error:
        validate_enum(value, allowed={"refund", "billing"}, field="category")
    assert error.value.field == "category"
    assert "private-label" not in str(error.value)


def test_enum_rejects_a_string_in_place_of_choices():
    with pytest.raises(ValueError, match="collection"):
        validate_enum("fund", allowed="refund", field="category")


@pytest.mark.parametrize(
    "value",
    [
        "A concise explanation.",
        "  Où est mon colis ?  ",
        "配送が遅れています。📦",
        "é" * 300,
    ],
    ids=["plain", "spacing", "unicode", "boundary"],
)
def test_text_preserves_valid_unicode_spacing_and_length(value):
    assert validate_text_field(value, field="explanation", max_length=300) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        None,
        33,
        [],
        "unsafe\nline",
        "unsafe\rline",
        "unsafe\tline",
        "unsafe\x1bescape",
        pytest.param("private-text" * 30, id="overlong"),
        pytest.param("\ud800", id="surrogate"),
    ],
)
def test_text_rejects_wrong_type_length_blank_and_controls(value):
    with pytest.raises(InvalidOutputField) as error:
        validate_text_field(value, field="explanation", max_length=300)
    assert error.value.field == "explanation"
    assert "private-text" not in str(error.value) and "unsafe" not in str(error.value)
