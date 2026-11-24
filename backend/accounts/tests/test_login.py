from uuid import uuid4

import pytest
from django.contrib.sessions.models import Session
from django.db import DatabaseError
from django.urls import reverse

from accounts.roles import SUPPORT_AGENT_GROUP

from . import postgres_account_tests

pytestmark = postgres_account_tests
CSRF_URL = reverse("accounts:csrf")
LOGIN_URL = reverse("accounts:login")


def test_login_creates_database_session_and_returns_minimal_profile(
    browser_client, agent
):
    account, credentials = agent
    csrf = browser_client.get(CSRF_URL).json()["csrfToken"]
    response = browser_client.post(
        LOGIN_URL, credentials, format="json", HTTP_X_CSRFTOKEN=csrf
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": account.pk,
        "username": account.username,
        "role": "support_agent",
        "is_authenticated": True,
    }
    assert Session.objects.filter(
        session_key=browser_client.cookies["sessionid"].value
    ).exists()
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.parametrize(
    "rejection", ["incorrect", "unknown", "inactive", "unassigned", "staff"]
)
def test_credential_failures_share_response_and_create_no_session(
    browser_client, make_account, rejection
):
    if rejection == "unknown":
        credentials = {"username": str(uuid4()), "password": str(uuid4())}
    elif rejection in {"unassigned", "staff"}:
        _, credentials = make_account(is_staff=rejection == "staff")
    else:
        _, credentials = make_account(
            SUPPORT_AGENT_GROUP, is_active=rejection != "inactive"
        )
        if rejection == "incorrect":
            credentials["password"] = str(uuid4())

    csrf = browser_client.get(CSRF_URL).json()["csrfToken"]
    response = browser_client.post(
        LOGIN_URL, credentials, format="json", HTTP_X_CSRFTOKEN=csrf
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid credentials or insufficient account access."
    }
    assert "sessionid" not in response.cookies
    assert not Session.objects.exists()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "name"},
        {"password": "value"},
        {"username": "", "password": "value"},
        {"username": " \t", "password": "value"},
        {"username": "name", "password": ""},
        {"username": "name", "password": 123},
        {"username": "name", "password": "value", "role": "superuser"},
        {"username": "a" * 151, "password": "value"},
        {"username": "name", "password": "a" * 4097},
        ["value"],
    ],
)
def test_login_rejects_invalid_schema_before_authentication(
    browser_client, monkeypatch, payload
):
    def unexpected_authentication(*args, **kwargs):
        pytest.fail("Invalid credentials payload reached the authentication backend")

    monkeypatch.setattr("accounts.views.authenticate", unexpected_authentication)
    token = browser_client.get(CSRF_URL).json()["csrfToken"]
    response = browser_client.post(
        LOGIN_URL, payload, format="json", HTTP_X_CSRFTOKEN=token
    )

    assert response.status_code == 400
    assert "sessionid" not in response.cookies


def test_login_preserves_password_whitespace(browser_client, agent):
    account, credentials = agent
    credentials["password"] = f"  {credentials['password']}  "
    account.set_password(credentials["password"])
    account.save(update_fields=["password"])
    token = browser_client.get(CSRF_URL).json()["csrfToken"]

    assert (
        browser_client.post(
            LOGIN_URL,
            credentials,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )


def test_unexpected_login_error_omits_diagnostics(
    browser_client, settings, monkeypatch, caplog
):
    settings.DEBUG = True
    marker = uuid4().hex

    def failed_authentication(*args, **kwargs):
        raise DatabaseError(marker)

    monkeypatch.setattr("accounts.views.authenticate", failed_authentication)
    token = browser_client.get(CSRF_URL).json()["csrfToken"]
    response = browser_client.post(
        LOGIN_URL,
        {"username": "name", "password": marker},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected server error occurred."}
    assert marker not in caplog.text


def test_login_throttles_by_direct_peer_and_resets_after_window(
    browser_client, monkeypatch
):
    now = 100.0
    monkeypatch.setattr("accounts.throttling.monotonic", lambda: now)
    token = browser_client.get(CSRF_URL).json()["csrfToken"]
    for _ in range(10):
        response = browser_client.post(
            LOGIN_URL, {}, format="json", HTTP_X_CSRFTOKEN=token
        )
        assert response.status_code == 400

    response = browser_client.post(
        LOGIN_URL,
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_X_FORWARDED_FOR="192.0.2.10",
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert (
        browser_client.post(
            LOGIN_URL,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            REMOTE_ADDR="192.0.2.10",
        ).status_code
        == 400
    )
    now += 60
    assert (
        browser_client.post(
            LOGIN_URL, {}, format="json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 400
    )
