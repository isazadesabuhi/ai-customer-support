import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from ai.client import get_llm_client
from ai.configuration import LLMConfig
from ai.errors import LLMError
from ai.sentiment_urgency.errors import SentimentUrgencyError
from ai.sentiment_urgency.prompts import (
    PROMPT_VERSION,
    build_sentiment_urgency_messages,
)
from ai.sentiment_urgency.service import (
    ANALYSIS_OUTPUT_TOKENS,
    SentimentUrgencyAnalyzer,
)


class Command(BaseCommand):
    help = "Validate a fictional message locally. Add --live for potentially billable sentiment and urgency analysis."

    def add_arguments(self, parser):
        parser.add_argument("--text", required=True, help="A fictional sample message.")
        parser.add_argument(
            "--live",
            action="store_true",
            help="Request real sentiment and urgency analysis.",
        )

    def handle(self, *args, text, live, **options):
        try:
            if not live:
                build_sentiment_urgency_messages(text)
                self.stdout.write(
                    f"Offline validation passed for {PROMPT_VERSION}. No model request was sent."
                )
                return

            config = LLMConfig.from_environment()
            analyzer = SentimentUrgencyAnalyzer(
                get_llm_client(config),
                max_output_tokens=min(ANALYSIS_OUTPUT_TOKENS, config.max_output_tokens),
            )
            result = analyzer.analyze(text)
        except (SentimentUrgencyError, LLMError) as error:
            raise CommandError(str(error)) from None

        self.stdout.write(json.dumps(asdict(result)))
