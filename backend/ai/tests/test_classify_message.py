import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ai.errors import LLMRateLimitError
from ai.schemas import LLMResponse, LLMUsage
from ai.testing import FakeLLMClient

COMMAND = "ai.management.commands.classify_message"


def test_default_command_validates_without_credentials_or_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(
        f"{COMMAND}.get_llm_client", lambda *_: pytest.fail("Live client constructed")
    )
    stdout = StringIO()

    call_command("classify_message", text="Where is my order?", stdout=stdout)

    assert "classification-v1" in stdout.getvalue()
    assert "No model request was sent." in stdout.getvalue()
    assert "Where is my order?" not in stdout.getvalue()


def test_default_command_rejects_blank_text():
    with pytest.raises(CommandError, match="nonblank"):
        call_command("classify_message", text=" \t", stdout=StringIO())


def test_live_requires_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        f"{COMMAND}.get_llm_client", lambda *_: pytest.fail("Live client constructed")
    )
    with pytest.raises(CommandError, match="OPENAI_API_KEY"):
        call_command(
            "classify_message", text="Where is my order?", live=True, stdout=StringIO()
        )


def test_live_command_prints_validated_result_and_applies_existing_budget(
    llm_env, monkeypatch
):
    llm_env.setenv("LLM_MAX_OUTPUT_TOKENS", "96")
    fake = FakeLLMClient(
        LLMResponse(
            '{"category":"shipping","explanation":"The customer asks about delivery."}',
            "fake",
            "test-model",
            LLMUsage(18, 8, 26),
            "req_test",
        )
    )

    def get_client(config):
        assert config.max_retries == 2
        return fake

    monkeypatch.setattr(f"{COMMAND}.get_llm_client", get_client)
    stdout = StringIO()
    call_command(
        "classify_message", text="Where is my order?", live=True, stdout=stdout
    )

    assert len(fake.calls) == 1
    assert fake.calls[0].max_output_tokens == 96
    assert "test-only-secret" not in stdout.getvalue()
    assert "Where is my order?" not in stdout.getvalue()
    assert json.loads(stdout.getvalue()) == {
        "category": "shipping",
        "explanation": "The customer asks about delivery.",
        "prompt_version": "classification-v1",
        "provider": "fake",
        "model": "test-model",
        "usage": {"input_tokens": 18, "output_tokens": 8, "total_tokens": 26},
        "provider_request_id": "req_test",
    }


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (LLMRateLimitError("Provider rate limit."), "rate limit"),
        (
            LLMResponse("private malformed response", "fake", "test-model"),
            "single JSON object",
        ),
    ],
)
def test_live_command_errors_are_safe(llm_env, monkeypatch, outcome, expected):
    fake = FakeLLMClient(outcome)
    monkeypatch.setattr(f"{COMMAND}.get_llm_client", lambda _: fake)
    stdout = StringIO()
    with pytest.raises(CommandError, match=expected) as error:
        call_command(
            "classify_message", text="Where is my order?", live=True, stdout=stdout
        )
    assert "private malformed response" not in str(error.value)
    assert stdout.getvalue() == ""
    assert len(fake.calls) == 1
