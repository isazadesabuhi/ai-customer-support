from typing import Literal

JSONErrorCode = Literal[
    "nonblank", "duplicate", "invalid", "nonfinite", "size", "nesting"
]


class StructuredOutputError(Exception):
    """A sanitized error raised at the structured-output boundary."""


class InvalidJSONOutput(StructuredOutputError):
    def __init__(self, code: JSONErrorCode, message: str):
        super().__init__(message)
        self.code = code


class InvalidOutputShape(StructuredOutputError):
    pass


class InvalidOutputField(StructuredOutputError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
