from collections.abc import Collection, Mapping

from .errors import InvalidOutputField, InvalidOutputShape


def require_fields(
    data: Mapping[str, object],
    *,
    required: frozenset[str],
    allowed: frozenset[str] | None = None,
) -> None:
    """Require exactly the required keys unless optional keys are explicitly allowed."""
    permitted = required if allowed is None else allowed
    if not required <= permitted:
        raise InvalidOutputShape("Required fields must also be allowed.")
    if not isinstance(data, Mapping):
        raise InvalidOutputShape("Output fields require a JSON object.")

    missing = required - data.keys()
    unexpected = data.keys() - permitted
    if missing or unexpected:
        raise InvalidOutputShape(
            f"Output has {len(missing)} missing required field(s) and {len(unexpected)} unexpected field(s)."
        )


def validate_enum(value: object, *, allowed: Collection[str], field: str) -> str:
    """Accept only exact string values from code-owned choices."""
    if isinstance(allowed, str):
        raise ValueError("Allowed choices must be a collection of labels.")
    if not isinstance(value, str) or value not in allowed:
        raise InvalidOutputField(
            field, f"Output field '{field}' has an unsupported label."
        )
    return value


def validate_text_field(value: object, *, field: str, max_length: int) -> str:
    """Keep printable, nonblank text in its original form."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isprintable()
        or len(value) > max_length
    ):
        raise InvalidOutputField(
            field,
            f"Output field '{field}' must be nonblank printable text of at most {max_length} characters.",
        )
    return value
