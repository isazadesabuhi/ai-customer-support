import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from ai.client import get_llm_client
from ai.configuration import LLMConfig
from ai.draft_generation import CustomerResponseDraftGenerator, DraftGenerationRequest
from ai.draft_generation.errors import DraftGenerationError
from ai.draft_generation.prompts import PROMPT_VERSION
from ai.draft_generation.schemas import LANGUAGES, TONES
from ai.draft_generation.service import DRAFT_OUTPUT_TOKENS
from ai.errors import LLMError


class Command(BaseCommand):
    help = "Validate fictional draft inputs locally. Add --live for a potentially billable draft request. Use only fictional data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--text", required=True, help="A fictional customer message."
        )
        parser.add_argument("--language", choices=LANGUAGES, default="en")
        parser.add_argument("--tone", choices=TONES, default="professional")
        parser.add_argument("--context", help="Fictional business facts for the draft.")
        parser.add_argument("--live", action="store_true", help="Request a real draft.")

    def handle(self, *args, text, language, tone, context, live, **options):
        try:
            request = DraftGenerationRequest(
                text, tone=tone, language=language, context=context
            )
            if not live:
                self.stdout.write(
                    f"Offline validation passed for {PROMPT_VERSION}. No draft was generated or model request sent."
                )
                return

            self.stderr.write("Use only fictional data for manual draft generation.")
            config = LLMConfig.from_environment()
            generator = CustomerResponseDraftGenerator(
                get_llm_client(config),
                max_output_tokens=min(DRAFT_OUTPUT_TOKENS, config.max_output_tokens),
            )
            result = generator.generate(request)
        except (DraftGenerationError, LLMError) as error:
            raise CommandError(str(error)) from None

        self.stdout.write("Human review required.")
        self.stdout.write(json.dumps(asdict(result)))
