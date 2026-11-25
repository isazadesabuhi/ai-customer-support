class LLMError(Exception):
    """A sanitized provider-independent failure."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class LLMConfigurationError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMConnectionError(LLMError):
    pass


class LLMInvalidRequestError(LLMError):
    pass


class LLMProviderError(LLMError):
    pass


class LLMInvalidResponseError(LLMError):
    pass
