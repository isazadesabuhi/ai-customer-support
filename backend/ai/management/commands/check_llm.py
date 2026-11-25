from dataclasses import replace
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from ai.client import get_llm_client
from ai.configuration import LLMConfig
from ai.errors import LLMError, LLMInvalidResponseError
from ai.schemas import LLMMessage


class Command(BaseCommand):
    help = "Validate LLM configuration. Add --live to send one potentially billable smoke request."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Send one short OpenAI request without retries.",
        )

    def handle(self, *args, live, **options):
        try:
            config = LLMConfig.from_environment()
            self.stdout.write(f"Provider: {config.provider}")
            self.stdout.write(f"Model: {config.model}")
            if not live:
                self.stdout.write(
                    self.style.SUCCESS(
                        "LLM configuration is valid. No request was sent."
                    )
                )
                return

            client = get_llm_client(replace(config, max_retries=0))
            start = perf_counter()
            result = client.generate(
                [LLMMessage(role="user", content="Reply with exactly the word READY.")],
                max_output_tokens=min(64, config.max_output_tokens),
            )
            if not result.text.strip():
                raise LLMInvalidResponseError("The provider returned no usable text.")
        except LLMError as error:
            raise CommandError(str(error)) from None

        self.stdout.write(
            self.style.SUCCESS(
                f"Live request succeeded in {perf_counter() - start:.2f} seconds."
            )
        )
        self.stdout.write(
            f"Usage returned: {'yes' if result.usage is not None else 'no'}"
        )
        if result.usage is not None:
            for label, value in (
                ("Input tokens", result.usage.input_tokens),
                ("Output tokens", result.usage.output_tokens),
                ("Total tokens", result.usage.total_tokens),
            ):
                if value is not None:
                    self.stdout.write(f"{label}: {value}")
