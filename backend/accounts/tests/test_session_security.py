from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from support.models import Conversation, Customer, Message

from . import postgres_account_tests

pytestmark = postgres_account_tests
CSRF_URL = reverse("accounts:csrf")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
ME_URL = reverse("accounts:me")


@pytest.mark.parametrize("invalid_token", [None, "a" * 64])
def test_anonymous_login_checks_csrf_before_authenticating(
    browser_client, agent, invalid_token
):
    _, credentials = agent
    browser_client.get(CSRF_URL)
    headers = {"HTTP_X_CSRFTOKEN": invalid_token} if invalid_token else {}

    response = browser_client.post(LOGIN_URL, credentials, format="json", **headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF verification failed."}
    assert "sessionid" not in browser_client.cookies
    assert not Session.objects.exists()


def test_login_rotates_anonymous_session_and_csrf_cookie(browser_client, agent):
    _, credentials = agent
    session = browser_client.session
    session["marker"] = True
    session.save()
    old_session = session.session_key
    old_token = browser_client.get(CSRF_URL).json()["csrfToken"]
    old_cookie = browser_client.cookies["csrftoken"].value

    response = browser_client.post(
        LOGIN_URL, credentials, format="json", HTTP_X_CSRFTOKEN=old_token
    )

    assert response.status_code == 200
    assert browser_client.session.session_key != old_session
    assert not Session.objects.filter(session_key=old_session).exists()
    assert browser_client.cookies["csrftoken"].value != old_cookie
    assert (
        browser_client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=old_token).status_code == 403
    )
    new_token = browser_client.get(CSRF_URL).json()["csrfToken"]
    assert (
        browser_client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=new_token).status_code == 204
    )


def test_real_session_requires_csrf_on_both_support_writes(signed_in):
    client, csrf = signed_in
    customer = Customer.objects.create(name="Example", email="example@example.test")
    conversations_url = reverse("support:conversation-list")
    payload = {"customer_id": str(customer.pk), "subject": "Order question"}
    assert client.get(conversations_url).status_code == 200
    assert client.post(conversations_url, payload, format="json").status_code == 403
    assert not Conversation.objects.exists()

    created = client.post(
        conversations_url, payload, format="json", HTTP_X_CSRFTOKEN=csrf
    )
    assert created.status_code == 201
    messages_url = reverse("support:conversation-messages", args=[created.json()["id"]])
    message = {"sender": "agent", "content": "How can I help?"}
    assert client.post(messages_url, message, format="json").status_code == 403
    assert not Message.objects.exists()
    assert (
        client.post(
            messages_url, message, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 201
    )


def test_logout_invalidates_session_and_old_cookie(signed_in):
    client, csrf = signed_in
    old_session = client.cookies["sessionid"].value
    assert client.get(LOGOUT_URL).status_code == 405
    assert client.post(LOGOUT_URL).status_code == 403
    assert client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN="a" * 64).status_code == 403
    assert client.get(ME_URL).status_code == 200

    response = client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf)

    assert response.status_code == 204
    assert response.content == b""
    assert response.cookies["sessionid"]["max-age"] == 0
    assert not Session.objects.filter(session_key=old_session).exists()
    assert client.get(ME_URL).status_code == 403
    replay = APIClient(enforce_csrf_checks=True)
    replay.cookies["sessionid"] = old_session
    assert replay.get(ME_URL).status_code == 403
    assert replay.get(reverse("support:conversation-list")).status_code == 403


def test_anonymous_logout_is_denied(browser_client):
    assert browser_client.post(LOGOUT_URL).status_code == 403


@pytest.mark.parametrize("change", ["expired", "inactive", "password"])
def test_session_stops_authorizing_after_identity_changes(signed_in, agent, change):
    client, _ = signed_in
    account, credentials = agent
    if change == "expired":
        Session.objects.filter(session_key=client.cookies["sessionid"].value).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
    elif change == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    else:
        account.set_password(credentials["password"] + "-changed")
        account.save(update_fields=["password"])

    assert client.get(ME_URL).status_code == 403
    assert client.get(reverse("support:conversation-list")).status_code == 403


@pytest.mark.parametrize("secure", [False, True], ids=["development", "https"])
def test_login_response_sets_cookie_security_flags(
    browser_client, agent, settings, secure
):
    settings.SESSION_COOKIE_SECURE = settings.CSRF_COOKIE_SECURE = secure
    _, credentials = agent
    token = browser_client.get(CSRF_URL, secure=secure).json()["csrfToken"]
    origin = "https://testserver" if secure else "http://localhost:3000"

    response = browser_client.post(
        LOGIN_URL,
        credentials,
        format="json",
        secure=secure,
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN=origin,
    )

    assert response.status_code == 200
    session_cookie = response.cookies["sessionid"]
    assert session_cookie["max-age"] == 8 * 60 * 60
    for name in ("sessionid", "csrftoken"):
        cookie = response.cookies[name]
        assert cookie["httponly"]
        assert bool(cookie["secure"]) is secure
        assert cookie["samesite"] == "Lax"
        assert not cookie["domain"]
