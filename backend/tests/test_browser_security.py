from runpy import run_module

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from rest_framework.test import APIClient

CSRF_URL = reverse("accounts:csrf")
LOGIN_URL = reverse("accounts:login")


def test_csrf_bootstrap_sets_masked_token_and_cookie_without_session():
    response = APIClient(enforce_csrf_checks=True).get(CSRF_URL)

    assert response.status_code == 200
    assert set(response.json()) == {"csrfToken"}
    token = response.json()["csrfToken"]
    cookie = response.cookies["csrftoken"]
    assert len(token) == 64 and len(cookie.value) == 32
    assert cookie["httponly"] and cookie["samesite"] == "Lax"
    assert "sessionid" not in response.cookies
    assert "no-store" in response.headers["Cache-Control"]


def test_explicit_local_origin_is_allowed_on_api_preflight():
    response = APIClient().options(
        LOGIN_URL,
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-csrftoken",
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "x-csrftoken" in response.headers["Access-Control-Allow-Headers"]
    assert response.headers["Access-Control-Expose-Headers"] == "retry-after"
    assert "origin" in response.headers["Vary"].lower()


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:3000", "https://untrusted.example", "null"]
)
def test_unconfigured_origins_get_no_cors_access_and_cannot_submit_csrf(origin):
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(CSRF_URL, HTTP_ORIGIN=origin)
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers

    rejected = client.post(
        LOGIN_URL,
        {},
        format="json",
        HTTP_ORIGIN=origin,
        HTTP_X_CSRFTOKEN=response.json()["csrfToken"],
    )
    assert rejected.status_code == 403


def test_cors_is_limited_to_api_paths():
    response = APIClient().get("/", HTTP_ORIGIN="http://localhost:3000")
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.fixture
def runtime_environment(monkeypatch):
    monkeypatch.delenv("DJANGO_FRONTEND_ORIGINS", raising=False)
    monkeypatch.setenv("DJANGO_ENV", "production")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-signing-key")
    monkeypatch.setenv("POSTGRES_DB", "support_example")
    monkeypatch.setenv("POSTGRES_USER", "support_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-only-db-password")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "5432")
    return monkeypatch


def test_production_uses_secure_cookies_and_empty_origin_allowlist(runtime_environment):
    config = run_module("config.settings")
    assert config["SESSION_COOKIE_SECURE"] and config["CSRF_COOKIE_SECURE"]
    assert config["CORS_ALLOWED_ORIGINS"] == config["CSRF_TRUSTED_ORIGINS"] == []
    assert not config["CORS_ALLOW_ALL_ORIGINS"]


def test_development_bootstraps_only_localhost_origin(runtime_environment):
    runtime_environment.setenv("DJANGO_ENV", "development")
    config = run_module("config.settings")
    assert not config["SESSION_COOKIE_SECURE"] and not config["CSRF_COOKIE_SECURE"]
    assert (
        config["CORS_ALLOWED_ORIGINS"]
        == config["CSRF_TRUSTED_ORIGINS"]
        == ["http://localhost:3000"]
    )


def test_configured_https_origins_are_used_for_cors_and_csrf(runtime_environment):
    runtime_environment.setenv(
        "DJANGO_FRONTEND_ORIGINS",
        "https://app.example.test, https://preview.example.test",
    )
    config = run_module("config.settings")
    assert (
        config["CORS_ALLOWED_ORIGINS"]
        == config["CSRF_TRUSTED_ORIGINS"]
        == ["https://app.example.test", "https://preview.example.test"]
    )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.test",
        "http://localhost:3000",
        "null",
        "https://example.test/",
        "https://example.test?",
        "https://name:password@example.test",
        "https://example.test:99999",
    ],
)
def test_invalid_origin_fails_closed(runtime_environment, origin):
    runtime_environment.setenv("DJANGO_FRONTEND_ORIGINS", origin)
    with pytest.raises(ImproperlyConfigured, match="DJANGO_FRONTEND_ORIGINS") as error:
        run_module("config.settings")
    assert "password" not in str(error.value)
