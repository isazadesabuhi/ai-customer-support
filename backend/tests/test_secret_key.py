from runpy import run_module

import pytest
from django.core.exceptions import ImproperlyConfigured


@pytest.fixture(autouse=True)
def database_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "support_example")
    monkeypatch.setenv("POSTGRES_USER", "support_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "example-password")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "5432")


@pytest.mark.parametrize(
    ("environment", "secret", "debug"),
    [
        (None, None, "false"),
        ("production", "", "false"),
        ("staging", " \t ", "false"),
        (None, None, "true"),
    ],
)
def test_runtime_requires_a_non_empty_key_outside_development(
    monkeypatch, environment, secret, debug
):
    monkeypatch.delenv("DJANGO_ENV", raising=False)
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    monkeypatch.setenv("DJANGO_DEBUG", debug)
    if environment is not None:
        monkeypatch.setenv("DJANGO_ENV", environment)
    if secret is not None:
        monkeypatch.setenv("DJANGO_SECRET_KEY", secret)

    with pytest.raises(ImproperlyConfigured, match="Set a non-empty DJANGO_SECRET_KEY"):
        run_module("config.settings")


def test_explicit_development_generates_a_key_without_enabling_debug(monkeypatch):
    monkeypatch.setenv("DJANGO_ENV", "development")
    monkeypatch.setenv("DJANGO_SECRET_KEY", " ")
    monkeypatch.delenv("DJANGO_DEBUG", raising=False)
    monkeypatch.setattr(
        "django.core.management.utils.get_random_secret_key",
        lambda: "generated-test-key",
    )

    settings = run_module("config.settings")

    assert settings["SECRET_KEY"] == "generated-test-key"
    assert settings["DEBUG"] is False


@pytest.mark.parametrize("environment", [None, "development", "production"])
def test_explicit_key_is_preserved(monkeypatch, environment):
    monkeypatch.delenv("DJANGO_ENV", raising=False)
    monkeypatch.delenv("DJANGO_DEBUG", raising=False)
    if environment is not None:
        monkeypatch.setenv("DJANGO_ENV", environment)
    monkeypatch.setenv("DJANGO_SECRET_KEY", " test-supplied-secret ")

    assert run_module("config.settings")["SECRET_KEY"] == " test-supplied-secret "
