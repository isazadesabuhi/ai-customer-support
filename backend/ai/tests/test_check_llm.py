from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ai.errors import LLMRateLimitError
from ai.schemas import LLMResponse, LLMUsage
from ai.testing import FakeLLMClient

COMMAND = "ai.management.commands.check_llm"


def test_default_mode_validates_config_without_creating_client(llm_env, monkeypatch):
    monkeypatch.setattr(
        f"{COMMAND}.get_llm_client", lambda *_: pytest.fail("Live client constructed")
    )
    output = StringIO()
    call_command("check_llm", stdout=output)
    assert "Provider: openai" in output.getvalue()
    assert "No request was sent." in output.getvalue()
    assert "test-only-secret" not in output.getvalue()


@pytest.mark.parametrize("live", [False, True])
def test_check_requires_configuration(llm_env, live):
    llm_env.delenv("OPENAI_API_KEY")
    with pytest.raises(CommandError, match="OPENAI_API_KEY"):
        call_command("check_llm", live=live)


@pytest.mark.parametrize("usage", [None, LLMUsage(8, None, 10)])
def test_live_command_uses_one_capped_call_and_omits_text(llm_env, monkeypatch, usage):
    fake = FakeLLMClient(
        LLMResponse("Private generated text", "fake", "test-model", usage)
    )
    llm_env.setenv("LLM_MAX_OUTPUT_TOKENS", "32")

    def get_client(config):
        assert config.max_retries == 0
        return fake

    monkeypatch.setattr(f"{COMMAND}.get_llm_client", get_client)
    output = StringIO()
    call_command("check_llm", live=True, stdout=output)
    assert len(fake.calls) == 1 and fake.calls[0].max_output_tokens == 32
    assert fake.calls[0].messages[0].content == "Reply with exactly the word READY."
    assert "Live request succeeded" in output.getvalue()
    assert "Private generated text" not in output.getvalue()
    assert "test-only-secret" not in output.getvalue()
    assert "Output tokens:" not in output.getvalue()
    if usage:
        assert "Input tokens: 8" in output.getvalue()
        assert "Total tokens: 10" in output.getvalue()
    else:
        assert "Usage returned: no" in output.getvalue()


@pytest.mark.parametrize(
    "outcome, message",
    [
        (LLMRateLimitError("OpenAI rate limit reached."), "rate limit"),
        (LLMResponse(" ", "fake", "test-model"), "no usable text"),
    ],
)
def test_live_command_surfaces_sanitized_failure(
    llm_env, monkeypatch, outcome, message
):
    fake = FakeLLMClient(outcome)
    monkeypatch.setattr(f"{COMMAND}.get_llm_client", lambda _: fake)
    with pytest.raises(CommandError, match=message) as error:
        call_command("check_llm", live=True, stdout=StringIO())
    assert "test-only-secret" not in str(error.value)
