class ClassificationError(Exception):
    """The classification input or output violated the service contract."""


class InvalidClassificationInput(ClassificationError):
    pass


class InvalidClassificationOutput(ClassificationError):
    pass
