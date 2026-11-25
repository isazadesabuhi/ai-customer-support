import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from ai.classification.errors import ClassificationError
from ai.classification.prompts import PROMPT_VERSION, build_classification_messages
from ai.classification.service import (
    CLASSIFICATION_OUTPUT_TOKENS,
    CustomerMessageClassifier,
)
from ai.client import get_llm_client
from ai.configuration import LLMConfig
from ai.errors import LLMError


class Command(BaseCommand):
    help = "Validate a fictional message locally. Add --live for potentially billable classification."

    def add_arguments(self, parser):
        parser.add_argument("--text", required=True, help="A fictional sample message.")
        parser.add_argument(
            "--live", action="store_true", help="Request a real classification."
        )

    def handle(self, *args, text, live, **options):
        try:
            if not live:
                build_classification_messages(text)
                self.stdout.write(
                    f"Input is valid for {PROMPT_VERSION}. No model request was sent."
                )
                return

            config = LLMConfig.from_environment()
            classifier = CustomerMessageClassifier(
                get_llm_client(config),
                max_output_tokens=min(
                    CLASSIFICATION_OUTPUT_TOKENS, config.max_output_tokens
                ),
            )
            result = classifier.classify(text)
        except (ClassificationError, LLMError) as error:
            raise CommandError(str(error)) from None

        self.stdout.write(json.dumps(asdict(result)))
