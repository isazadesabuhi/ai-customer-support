import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ai.errors import LLMTimeoutError
from ai.schemas import LLMResponse, LLMUsage
from ai.sentiment_urgency.service import ANALYSIS_OUTPUT_TOKENS
from ai.testing import FakeLLMClient

COMMAND = "ai.management.commands.analyze_sentiment"
MESSAGE = "I need my replacement before tomorrow."


def test_offline_command_requires_no_credentials_or_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(
        f"{COMMAND}.get_llm_client", lambda *_: pytest.fail("Live client constructed")
    )
    stdout = StringIO()

    call_command("analyze_sentiment", text=MESSAGE, stdout=stdout)

    assert "Offline validation passed for sentiment-urgency-v1" in stdout.getvalue()
    assert "No model request was sent." in stdout.getvalue()
    assert MESSAGE not in stdout.getvalue()


def test_offline_command_rejects_blank_message():
    with pytest.raises(CommandError, match="nonblank"):
        call_command("analyze_sentiment", text=" \t", stdout=StringIO())


def test_live_command_requires_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        f"{COMMAND}.get_llm_client", lambda *_: pytest.fail("Live client constructed")
    )
    with pytest.raises(CommandError, match="OPENAI_API_KEY"):
        call_command("analyze_sentiment", text=MESSAGE, live=True, stdout=StringIO())


@pytest.mark.parametrize("limit, expected", [(192, 192), (512, ANALYSIS_OUTPUT_TOKENS)])
def test_mocked_live_command_prints_validated_analysis_and_clamps_budget(
    llm_env, monkeypatch, limit, expected
):
    llm_env.setenv("LLM_MAX_OUTPUT_TOKENS", str(limit))
    payload = {
        "sentiment": "neutral",
        "urgency": "high",
        "sentiment_explanation": "The customer states a need factually.",
        "urgency_explanation": "The replacement is needed before tomorrow.",
    }
    fake = FakeLLMClient(
        LLMResponse(
            json.dumps(payload), "fake", "test-model", LLMUsage(22, 12, 34), "req_test"
        )
    )

    def get_client(config):
        assert config.max_retries == 2
        return fake

    monkeypatch.setattr(f"{COMMAND}.get_llm_client", get_client)
    stdout = StringIO()
    call_command("analyze_sentiment", text=MESSAGE, live=True, stdout=stdout)

    assert len(fake.calls) == 1 and fake.calls[0].max_output_tokens == expected
    assert fake.calls[0].messages[1].content == MESSAGE
    assert (
        "test-only-secret" not in stdout.getvalue() and MESSAGE not in stdout.getvalue()
    )
    assert json.loads(stdout.getvalue()) == payload | {
        "prompt_version": "sentiment-urgency-v1",
        "provider": "fake",
        "model": "test-model",
        "usage": {"input_tokens": 22, "output_tokens": 12, "total_tokens": 34},
        "provider_request_id": "req_test",
    }


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (LLMTimeoutError("Provider request timed out."), "timed out"),
        (
            LLMResponse("private malformed response", "fake", "test-model"),
            "single JSON object",
        ),
    ],
)
def test_mocked_live_failure_stays_safe(llm_env, monkeypatch, outcome, expected):
    fake = FakeLLMClient(outcome)
    monkeypatch.setattr(f"{COMMAND}.get_llm_client", lambda _: fake)
    stdout = StringIO()
    with pytest.raises(CommandError, match=expected) as error:
        call_command("analyze_sentiment", text=MESSAGE, live=True, stdout=stdout)
    assert "private malformed response" not in str(error.value)
    assert stdout.getvalue() == "" and len(fake.calls) == 1
