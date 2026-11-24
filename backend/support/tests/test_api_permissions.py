from base64 import b64encode
from uuid import uuid4

import pytest
from django.contrib.auth.models import Permission
from django.db import DatabaseError
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.roles import SUPPORT_AGENT_GROUP, SUPPORT_MANAGER_GROUP
from support.models import Conversation, Message
from support.permissions import HasSupportPermissions
from support.views import ConversationListView

from . import postgres_model_tests

pytestmark = postgres_model_tests

ENDPOINTS = (
    ("get", "conversation-list"),
    ("post", "conversation-list"),
    ("get", "conversation-detail"),
    ("get", "conversation-messages"),
    ("post", "conversation-messages"),
)


@pytest.mark.parametrize("method, endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "identity, allowed",
    [
        (SUPPORT_AGENT_GROUP, True),
        (SUPPORT_MANAGER_GROUP, True),
        ("staff", False),
        ("superuser", True),
    ],
)
def test_support_access_depends_on_role_and_permissions(
    method, endpoint, identity, allowed, conversation, django_user_model, support_groups
):
    user = django_user_model.objects.create_user(
        username="role-test",
        is_staff=identity == "staff",
        is_superuser=identity == "superuser",
    )
    if identity in support_groups:
        user.groups.add(support_groups[identity])
        assert not user.is_staff
    client = APIClient()
    client.force_login(user)
    args = [] if endpoint == "conversation-list" else [conversation.pk]
    url = reverse(f"support:{endpoint}", args=args)
    if method == "get":
        response = client.get(url)
        assert response.status_code == (200 if allowed else 403)
    else:
        payload = (
            {
                "customer_id": str(conversation.customer_id),
                "subject": "New conversation",
            }
            if endpoint == "conversation-list"
            else {"sender": "agent", "content": "Agent message"}
        )
        response = client.post(url, payload, format="json")
        assert response.status_code == (201 if allowed else 403)
        model = Conversation if endpoint == "conversation-list" else Message
        assert model.objects.count() == (model is Conversation) + allowed


@pytest.mark.parametrize(
    "method, endpoint, revoked",
    [
        ("get", "conversation-list", "view_conversation"),
        ("post", "conversation-list", "add_conversation"),
        ("get", "conversation-detail", "view_conversation"),
        ("get", "conversation-messages", "view_conversation"),
        ("get", "conversation-messages", "view_message"),
        ("post", "conversation-messages", "view_conversation"),
        ("post", "conversation-messages", "add_message"),
    ],
)
def test_individual_permission_revocation_is_enforced_on_existing_session(
    method, endpoint, revoked, conversation, agent_user, support_groups
):
    client = APIClient()
    client.force_login(agent_user)
    perm = Permission.objects.get(content_type__app_label="support", codename=revoked)
    group = support_groups[SUPPORT_AGENT_GROUP]
    group.permissions.remove(perm)

    args = [] if endpoint == "conversation-list" else [conversation.pk]
    url = reverse(f"support:{endpoint}", args=args)
    response = getattr(client, method)(url)

    assert response.status_code == 403
    assert Conversation.objects.count() == 1
    assert not Message.objects.exists()


def test_direct_permissions_without_role_do_not_grant_access(reviewer, support_groups):
    reviewer.user_permissions.set(support_groups[SUPPORT_AGENT_GROUP].permissions.all())
    client = APIClient()
    client.force_login(reviewer)

    assert client.get(reverse("support:conversation-list")).status_code == 403


@pytest.mark.parametrize("method, endpoint", ENDPOINTS)
@pytest.mark.parametrize("authenticated", [False, True], ids=["anonymous", "nonstaff"])
def test_access_denied_without_support_role(
    method, endpoint, authenticated, conversation, reviewer
):
    client = APIClient()
    if authenticated:
        client.force_authenticate(user=reviewer)
    args = [] if endpoint == "conversation-list" else [conversation.pk]
    url = reverse(f"support:{endpoint}", args=args) + "?is_staff=true&status=open"
    payload = (
        {"subject": "Private", "customer_id": str(conversation.customer_id)}
        if endpoint == "conversation-list"
        else {"sender": "agent", "content": "Private"}
    )
    response = (
        client.post(url, payload, format="json")
        if method == "post"
        else client.get(url)
    )

    assert response.status_code == 403
    assert set(response.json()) == {"detail"}
    assert conversation.customer.email not in response.content.decode()
    assert str(conversation.pk) not in response.content.decode()
    assert Conversation.objects.count() == 1
    assert not Message.objects.exists()


@pytest.mark.parametrize("method, endpoint", ENDPOINTS[2:])
def test_unassigned_user_cannot_enumerate_conversations(
    method, endpoint, conversation, reviewer
):
    client = APIClient()
    client.force_authenticate(user=reviewer)
    responses = [
        getattr(client, method)(reverse(f"support:{endpoint}", args=[pk]))
        for pk in (conversation.pk, uuid4(), "not-a-uuid")
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    assert len({response.content for response in responses}) == 1


@pytest.mark.parametrize("method, endpoint", ENDPOINTS[2:])
def test_parent_object_permission_is_checked(
    method, endpoint, conversation, agent_client, monkeypatch
):
    def deny(self, request, view, obj):
        assert obj.pk == conversation.pk
        return False

    monkeypatch.setattr(HasSupportPermissions, "has_object_permission", deny)
    response = getattr(agent_client, method)(
        reverse(f"support:{endpoint}", args=[conversation.pk])
    )

    assert response.status_code == 403
    assert not Message.objects.exists()


@pytest.mark.parametrize("method, endpoint", ENDPOINTS[2:])
def test_missing_or_malformed_uuid_returns_json_404(method, endpoint, agent_client):
    for pk in (uuid4(), "not-a-uuid"):
        response = getattr(agent_client, method)(
            reverse(f"support:{endpoint}", args=[pk])
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found."}


def test_updates_and_deletes_are_unavailable(agent_client, conversation):
    for endpoint in {endpoint for _, endpoint in ENDPOINTS}:
        args = [] if endpoint == "conversation-list" else [conversation.pk]
        url = reverse(f"support:{endpoint}", args=args)
        for method in ("put", "patch", "delete"):
            assert getattr(agent_client, method)(url).status_code == 405
    assert Conversation.objects.filter(pk=conversation.pk).exists()


def test_basic_authentication_is_rejected(agent_user):
    password = str(uuid4())
    agent_user.set_password(password)
    agent_user.save(update_fields=["password"])
    credentials = b64encode(f"{agent_user.username}:{password}".encode()).decode()
    response = APIClient().get(
        reverse("support:conversation-list"), HTTP_AUTHORIZATION=f"Basic {credentials}"
    )

    assert response.status_code == 403


def test_existing_session_authentication_enforces_csrf(agent_user, customer):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(agent_user)
    url = reverse("support:conversation-list")
    assert client.get(url).status_code == 200
    response = client.post(
        url, {"customer_id": str(customer.pk), "subject": "CSRF"}, format="json"
    )

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    assert not Conversation.objects.exists()


def test_unexpected_error_is_sanitized_with_debug_enabled(
    agent_client, settings, monkeypatch
):
    settings.DEBUG = True

    def fail(self):
        raise DatabaseError("private database diagnostics")

    monkeypatch.setattr(ConversationListView, "get_queryset", fail)
    response = agent_client.get(reverse("support:conversation-list"))

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected server error occurred."}
