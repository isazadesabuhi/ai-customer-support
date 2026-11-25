import os
import subprocess
import sys

import pytest
from django.core.management import call_command

from ai.client import get_llm_client
from ai.configuration import LLMConfig
from ai.errors import LLMConfigurationError
from ai.providers.openai import OpenAILLMClient


@pytest.mark.parametrize(
    "variable, value",
    [
        ("OPENAI_API_KEY", ""),
        ("OPENAI_API_KEY", "test secret"),
        ("OPENAI_MODEL", ""),
        ("OPENAI_MODEL", "invalid model"),
        ("OPENAI_MODEL", "test-only-secret"),
        ("LLM_PROVIDER", "fake"),
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "nan"),
        ("LLM_TIMEOUT_SECONDS", "121"),
        ("LLM_TIMEOUT_SECONDS", "not-a-number"),
        ("LLM_MAX_RETRIES", "-1"),
        ("LLM_MAX_RETRIES", "4"),
        ("LLM_MAX_RETRIES", "1.5"),
        ("LLM_MAX_OUTPUT_TOKENS", "15"),
        ("LLM_MAX_OUTPUT_TOKENS", "4097"),
        ("LLM_MAX_OUTPUT_TOKENS", "fast"),
    ],
)
def test_bad_environment_has_sanitized_error(llm_env, variable, value):
    llm_env.setenv(variable, value)
    with pytest.raises(LLMConfigurationError, match=variable) as exc:
        get_llm_client()
    assert "test-only-secret" not in str(exc.value)


def test_defaults_and_explicit_overrides(llm_env):
    default = LLMConfig.from_environment()
    assert (
        default.provider,
        default.timeout_seconds,
        default.max_retries,
        default.max_output_tokens,
    ) == ("openai", 30.0, 2, 500)

    llm_env.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    llm_env.setenv("LLM_MAX_RETRIES", "0")
    llm_env.setenv("LLM_MAX_OUTPUT_TOKENS", "256")
    config = LLMConfig.from_environment()
    assert (config.timeout_seconds, config.max_retries, config.max_output_tokens) == (
        12.5,
        0,
        256,
    )
    assert "test-only-secret" not in repr(config)
    assert isinstance(get_llm_client(), OpenAILLMClient)


def test_missing_credentials_do_not_affect_django_checks(llm_env):
    llm_env.delenv("OPENAI_API_KEY")
    llm_env.delenv("OPENAI_MODEL")
    call_command("check", verbosity=0)
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        get_llm_client()


def test_import_and_django_startup_do_not_construct_sdk():
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in {"OPENAI_API_KEY", "OPENAI_MODEL"}
    }
    script = "import sys, django; django.setup(); import ai.client; assert 'openai' not in sys.modules"
    subprocess.run([sys.executable, "-c", script], env=env, check=True, timeout=10)
