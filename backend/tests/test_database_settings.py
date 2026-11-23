from runpy import run_module

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.database import TEST_DATABASE_NAME, postgres_database


@pytest.fixture(autouse=True)
def database_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "support_example")
    monkeypatch.setenv("POSTGRES_USER", "support_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", " example password ")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)


def test_postgres_configuration_parses_environment_and_defaults():
    assert postgres_database() == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "support_example",
        "USER": "support_user",
        "PASSWORD": " example password ",
        "HOST": "127.0.0.1",
        "PORT": 5432,
        "OPTIONS": {"connect_timeout": 5},
    }


def test_runtime_uses_postgres_with_a_custom_port(monkeypatch):
    monkeypatch.setenv("DJANGO_ENV", "development")
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", " 55432 ")

    database = run_module("config.settings")["DATABASES"]["default"]

    assert database["ENGINE"] == "django.db.backends.postgresql"
    assert database["NAME"] == "support_example"
    assert database["HOST"] == "localhost"
    assert database["PORT"] == 55432


@pytest.mark.parametrize("name", ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"])
def test_runtime_rejects_missing_credentials_without_a_fallback(monkeypatch, name):
    monkeypatch.setenv("DJANGO_ENV", "development")
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.delenv(name)

    with pytest.raises(ImproperlyConfigured, match=name):
        run_module("config.settings")


@pytest.mark.parametrize("password", ["", " \t "])
def test_rejects_blank_password(monkeypatch, password):
    monkeypatch.setenv("POSTGRES_PASSWORD", password)

    with pytest.raises(ImproperlyConfigured, match="POSTGRES_PASSWORD"):
        postgres_database()


@pytest.mark.parametrize("port", ["", "abc", "1_000", "0", "65536"])
def test_rejects_invalid_port(monkeypatch, port):
    monkeypatch.setenv("DB_PORT", port)

    with pytest.raises(ImproperlyConfigured, match="DB_PORT"):
        postgres_database()


def test_rejects_blank_host(monkeypatch):
    monkeypatch.setenv("DB_HOST", " ")

    with pytest.raises(ImproperlyConfigured, match="DB_HOST"):
        postgres_database()


@pytest.mark.parametrize(
    "name", ["postgres", "template0", "template1", TEST_DATABASE_NAME]
)
def test_runtime_rejects_reserved_database_names(monkeypatch, name):
    monkeypatch.setenv("POSTGRES_DB", name)

    with pytest.raises(ImproperlyConfigured, match="reserved system or test database"):
        postgres_database()


def test_postgres_test_settings_select_an_isolated_database():
    database = run_module("config.postgres_test_settings")["DATABASES"]["default"]

    assert database["NAME"] == "postgres"
    assert database["OPTIONS"]["hostaddr"] == "127.0.0.1"
    assert database["TEST"]["NAME"] == TEST_DATABASE_NAME
    assert database["TEST"]["NAME"] != postgres_database()["NAME"]


def test_postgres_test_settings_reject_remote_hosts(monkeypatch):
    monkeypatch.setenv("DB_HOST", "postgres.example.invalid")

    with pytest.raises(ImproperlyConfigured, match="DB_HOST=127.0.0.1"):
        run_module("config.postgres_test_settings")
