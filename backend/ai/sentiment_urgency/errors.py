class SentimentUrgencyError(Exception):
    """The message or analysis output violated the service contract."""


class InvalidSentimentUrgencyInput(SentimentUrgencyError):
    pass


class InvalidSentimentUrgencyOutput(SentimentUrgencyError):
    pass
