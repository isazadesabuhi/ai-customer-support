from ..client import LLMClient
from .prompts import PROMPT_VERSION, build_sentiment_urgency_messages
from .schemas import SentimentUrgencyResult, parse_sentiment_urgency

ANALYSIS_OUTPUT_TOKENS = 384


class SentimentUrgencyAnalyzer:
    def __init__(
        self, llm_client: LLMClient, *, max_output_tokens: int = ANALYSIS_OUTPUT_TOKENS
    ):
        self._llm_client = llm_client
        self._max_output_tokens = max_output_tokens

    def analyze(self, message: str) -> SentimentUrgencyResult:
        response = self._llm_client.generate(
            build_sentiment_urgency_messages(message),
            max_output_tokens=self._max_output_tokens,
        )
        sentiment, urgency, sentiment_explanation, urgency_explanation = (
            parse_sentiment_urgency(response.text)
        )
        return SentimentUrgencyResult(
            sentiment=sentiment,
            urgency=urgency,
            sentiment_explanation=sentiment_explanation,
            urgency_explanation=urgency_explanation,
            prompt_version=PROMPT_VERSION,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
            provider_request_id=response.provider_request_id,
        )
