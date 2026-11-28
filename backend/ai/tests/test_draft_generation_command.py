import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ai.errors import LLMTimeoutError
from ai.management.commands import generate_draft
from ai.schemas import LLMResponse, LLMUsage
from ai.testing import FakeLLMClient


def test_offline_command_does_not_construct_client(monkeypatch):
    def forbidden(*args):
        pytest.fail("Offline validation accessed LLM configuration or client.")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(generate_draft.LLMConfig, "from_environment", forbidden)
    monkeypatch.setattr(generate_draft, "get_llm_client", forbidden)
    out = StringIO()
    call_command(
        "generate_draft",
        text="Où est ma commande ?",
        language="fr",
        tone="friendly",
        context="Statut inconnu.",
        stdout=out,
    )
    assert "Offline validation passed for draft-generation-v1." in out.getvalue()
    assert "No draft was generated or model request sent." in out.getvalue()
    assert "Statut inconnu." not in out.getvalue()


@pytest.mark.parametrize(
    ("text", "options"),
    [
        ("   ", {}),
        ("Hello", {"language": "de"}),
        ("Hello", {"tone": "other"}),
        ("Hello", {"context": " "}),
    ],
)
def test_command_validates_offline_configuration(text, options):
    with pytest.raises(CommandError):
        call_command("generate_draft", text=text, **options)


def test_live_command_requires_config_before_client(monkeypatch):
    def forbidden(*args):
        pytest.fail("The command attempted to create a client without credentials.")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(generate_draft, "get_llm_client", forbidden)
    with pytest.raises(CommandError, match="Set OPENAI_API_KEY"):
        call_command(
            "generate_draft", text="Where is my order?", live=True, stderr=StringIO()
        )


def test_live_command_shows_validated_draft_and_review(llm_env):
    llm_env.setenv("LLM_MAX_OUTPUT_TOKENS", "128")
    client = FakeLLMClient(
        LLMResponse(
            text='{"draft_text":"Bonjour !","needs_information":false,"information_needed":[]}',
            provider="fake",
            model="test-model",
            usage=LLMUsage(output_tokens=20),
            provider_request_id="req-fictional",
        )
    )
    llm_env.setattr(generate_draft, "get_llm_client", lambda config: client)
    stdout, stderr = StringIO(), StringIO()
    call_command(
        "generate_draft",
        text="Où est ma commande ?",
        language="fr",
        live=True,
        stdout=stdout,
        stderr=stderr,
    )
    heading, data = stdout.getvalue().splitlines()
    assert heading == "Human review required."
    assert json.loads(data) == {
        "draft_text": "Bonjour !",
        "needs_information": False,
        "information_needed": [],
        "requires_human_review": True,
        "prompt_version": "draft-generation-v1",
        "provider": "fake",
        "model": "test-model",
        "usage": {"input_tokens": None, "output_tokens": 20, "total_tokens": None},
        "provider_request_id": "req-fictional",
        "finish_reason": None,
    }
    assert "fictional data" in stderr.getvalue()
    assert "test-only-secret" not in stdout.getvalue() + stderr.getvalue()
    [call] = client.calls
    assert call.max_output_tokens == 128


@pytest.mark.parametrize(
    "outcome",
    [
        LLMTimeoutError("The provider timed out."),
        LLMResponse(
            text="Authorization: Bearer test-only-secret", provider="fake", model=None
        ),
    ],
)
def test_live_command_failures_are_safe(llm_env, outcome):
    client = FakeLLMClient(outcome)
    llm_env.setattr(generate_draft, "get_llm_client", lambda config: client)
    stdout = StringIO()
    with pytest.raises(CommandError) as caught:
        call_command(
            "generate_draft", text="Hello", live=True, stdout=stdout, stderr=StringIO()
        )
    assert not stdout.getvalue()
    assert "test-only-secret" not in str(caught.value)
    assert len(client.calls) == 1
