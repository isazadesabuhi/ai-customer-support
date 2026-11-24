import pytest
from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session
from django.urls import reverse

from accounts.roles import (
    SUPPORT_AGENT_GROUP,
    SUPPORT_MANAGER_GROUP,
    SUPPORT_PERMISSIONS,
)

from . import postgres_account_tests

pytestmark = postgres_account_tests
ME_URL = reverse("accounts:me")


@pytest.mark.parametrize(
    "roles, flags, expected",
    [
        ((SUPPORT_AGENT_GROUP,), {}, "support_agent"),
        ((SUPPORT_MANAGER_GROUP,), {}, "support_manager"),
        ((SUPPORT_AGENT_GROUP, SUPPORT_MANAGER_GROUP), {}, "support_manager"),
        ((), {"is_superuser": True}, "superuser"),
    ],
)
def test_current_user_reports_effective_role_and_only_support_permissions(
    browser_client, make_account, roles, flags, expected
):
    account, credentials = make_account(*roles, **flags)
    token = browser_client.get(reverse("accounts:csrf")).json()["csrfToken"]
    login = browser_client.post(
        reverse("accounts:login"), credentials, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert login.status_code == 200
    assert login.json()["role"] == expected
    response = browser_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json() == {
        "id": account.pk,
        "username": account.username,
        "role": expected,
        "permissions": list(SUPPORT_PERMISSIONS),
    }
    assert "private" in response.headers["Cache-Control"]


def test_anonymous_and_unassigned_users_are_denied(browser_client, make_account):
    assert browser_client.get(ME_URL).status_code == 403
    user, _ = make_account()
    browser_client.force_login(user)
    assert browser_client.get(ME_URL).status_code == 403


def test_group_removal_blocks_existing_session_but_still_allows_logout(
    signed_in, agent
):
    browser_client, csrf = signed_in
    user, _ = agent
    user.groups.clear()
    session_key = browser_client.cookies["sessionid"].value

    assert browser_client.get(ME_URL).status_code == 403
    assert browser_client.get(reverse("support:conversation-list")).status_code == 403
    assert (
        browser_client.post(
            reverse("accounts:logout"), HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 204
    )
    assert not Session.objects.filter(session_key=session_key).exists()


def test_permissions_profile_reflects_grants_and_excludes_unrelated_permissions(
    signed_in, agent
):
    browser_client, _ = signed_in
    user, _ = agent
    group = user.groups.get()
    group.permissions.remove(group.permissions.get(codename="view_message"))
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="auth", codename="view_user")
    )

    response = browser_client.get(ME_URL)
    assert response.status_code == 200
    assert response.json()["permissions"] == [
        p for p in SUPPORT_PERMISSIONS if p != "support.view_message"
    ]
