class DraftGenerationError(Exception):
    """The draft request or generated output violated the service contract."""


class InvalidDraftGenerationInput(DraftGenerationError):
    pass


class InvalidDraftGenerationOutput(DraftGenerationError):
    pass
