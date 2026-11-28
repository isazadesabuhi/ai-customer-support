import json
from math import isfinite
from typing import NoReturn

from .errors import InvalidJSONOutput

MAX_JSON_LENGTH = 16_384
MAX_JSON_DEPTH = 32


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, value in pairs:
        if name in fields:
            raise InvalidJSONOutput(
                "duplicate", "JSON output has a duplicate object key."
            )
        fields[name] = value
    return fields


def _reject_constant(_: str) -> NoReturn:
    raise InvalidJSONOutput(
        "nonfinite", "JSON output must contain only finite numbers."
    )


def _finite_float(value: str) -> float:
    number = float(value)
    if not isfinite(number):
        _reject_constant(value)
    return number


def _check_depth(payload: dict[str, object]) -> None:
    pending: list[tuple[dict[str, object] | list[object], int]] = [(payload, 1)]
    while pending:
        container, depth = pending.pop()
        if depth > MAX_JSON_DEPTH:
            raise InvalidJSONOutput("nesting", "JSON output is nested too deeply.")
        items = container.values() if isinstance(container, dict) else container
        pending.extend(
            (item, depth + 1) for item in items if isinstance(item, (dict, list))
        )


def parse_json_object(text: str) -> dict[str, object]:
    """Decode one bounded JSON object without coercion or syntax repair."""
    if not isinstance(text, str):
        raise InvalidJSONOutput("nonblank", "Output must be a nonblank JSON string.")
    if len(text) > MAX_JSON_LENGTH:
        raise InvalidJSONOutput(
            "size", f"JSON output exceeds {MAX_JSON_LENGTH} characters."
        )
    if not text.strip():
        raise InvalidJSONOutput("nonblank", "Output must be a nonblank JSON string.")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except RecursionError:
        error = InvalidJSONOutput("nesting", "JSON output is nested too deeply.")
    except ValueError:
        error = InvalidJSONOutput("invalid", "Output must be a single JSON object.")
    else:
        if not isinstance(payload, dict):
            raise InvalidJSONOutput("invalid", "Output must be a single JSON object.")
        _check_depth(payload)
        return payload
    # JSONDecodeError retains the entire document. Raise after leaving the handler.
    raise error
