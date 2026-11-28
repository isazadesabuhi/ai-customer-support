from ..client import LLMClient
from ..schemas import MIN_OUTPUT_TOKENS
from .errors import InvalidDraftGenerationInput
from .prompts import PROMPT_VERSION, build_draft_messages
from .schemas import DraftGenerationRequest, DraftGenerationResult, parse_draft_output

DRAFT_OUTPUT_TOKENS = 500


class CustomerResponseDraftGenerator:
    def __init__(
        self, llm_client: LLMClient, *, max_output_tokens: int = DRAFT_OUTPUT_TOKENS
    ):
        if (
            type(max_output_tokens) is not int
            or not MIN_OUTPUT_TOKENS <= max_output_tokens <= DRAFT_OUTPUT_TOKENS
        ):
            raise InvalidDraftGenerationInput(
                f"Draft output tokens must be an integer from {MIN_OUTPUT_TOKENS} to {DRAFT_OUTPUT_TOKENS}."
            )
        self._llm_client = llm_client
        self._max_output_tokens = max_output_tokens

    def generate(self, request: DraftGenerationRequest) -> DraftGenerationResult:
        if not isinstance(request, DraftGenerationRequest):
            raise InvalidDraftGenerationInput("Provide a DraftGenerationRequest.")
        response = self._llm_client.generate(
            build_draft_messages(request), max_output_tokens=self._max_output_tokens
        )
        draft_text, needs_information, information_needed = parse_draft_output(
            response.text
        )
        return DraftGenerationResult(
            draft_text=draft_text,
            needs_information=needs_information,
            information_needed=information_needed,
            prompt_version=PROMPT_VERSION,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
            provider_request_id=response.provider_request_id,
            finish_reason=response.finish_reason,
        )
