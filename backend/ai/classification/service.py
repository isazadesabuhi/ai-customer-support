from ..client import LLMClient
from .prompts import PROMPT_VERSION, build_classification_messages
from .schemas import ClassificationResult, parse_classification

CLASSIFICATION_OUTPUT_TOKENS = 256


class CustomerMessageClassifier:
    def __init__(
        self,
        llm_client: LLMClient,
        *,
        max_output_tokens: int = CLASSIFICATION_OUTPUT_TOKENS,
    ):
        self._llm_client = llm_client
        self._max_output_tokens = max_output_tokens

    def classify(self, message: str) -> ClassificationResult:
        response = self._llm_client.generate(
            build_classification_messages(message),
            max_output_tokens=self._max_output_tokens,
        )
        category, explanation = parse_classification(response.text)
        return ClassificationResult(
            category=category,
            explanation=explanation,
            prompt_version=PROMPT_VERSION,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
            provider_request_id=response.provider_request_id,
        )
