from base64 import b64encode
from uuid import uuid4

import pytest
from django.db import DatabaseError
from django.urls import reverse
from rest_framework.test import APIClient

from support.models import Conversation, Message
from support.permissions import IsSupportStaff
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
@pytest.mark.parametrize("authenticated", [False, True], ids=["anonymous", "nonstaff"])
def test_access_denied_without_staff(
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
def test_nonstaff_cannot_enumerate_conversations(
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
    method, endpoint, conversation, staff_client, monkeypatch
):
    def deny(self, request, view, obj):
        assert obj.pk == conversation.pk
        return False

    monkeypatch.setattr(IsSupportStaff, "has_object_permission", deny)
    response = getattr(staff_client, method)(
        reverse(f"support:{endpoint}", args=[conversation.pk])
    )

    assert response.status_code == 403
    assert not Message.objects.exists()


@pytest.mark.parametrize("method, endpoint", ENDPOINTS[2:])
def test_missing_or_malformed_uuid_returns_json_404(method, endpoint, staff_client):
    for pk in (uuid4(), "not-a-uuid"):
        response = getattr(staff_client, method)(
            reverse(f"support:{endpoint}", args=[pk])
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found."}


def test_updates_and_deletes_are_unavailable(staff_client, conversation):
    for endpoint in {endpoint for _, endpoint in ENDPOINTS}:
        args = [] if endpoint == "conversation-list" else [conversation.pk]
        url = reverse(f"support:{endpoint}", args=args)
        for method in ("put", "patch", "delete"):
            assert getattr(staff_client, method)(url).status_code == 405
    assert Conversation.objects.filter(pk=conversation.pk).exists()


def test_existing_basic_authentication_works(staff_user):
    password = str(uuid4())
    staff_user.set_password(password)
    staff_user.save(update_fields=["password"])
    credentials = b64encode(f"{staff_user.username}:{password}".encode()).decode()
    response = APIClient().get(
        reverse("support:conversation-list"), HTTP_AUTHORIZATION=f"Basic {credentials}"
    )

    assert response.status_code == 200


def test_existing_session_authentication_enforces_csrf(staff_user, customer):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff_user)
    url = reverse("support:conversation-list")
    assert client.get(url).status_code == 200
    response = client.post(
        url, {"customer_id": str(customer.pk), "subject": "CSRF"}, format="json"
    )

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    assert not Conversation.objects.exists()


def test_unexpected_error_is_sanitized_with_debug_enabled(
    staff_client, settings, monkeypatch
):
    settings.DEBUG = True

    def fail(self):
        raise DatabaseError("private database diagnostics")

    monkeypatch.setattr(ConversationListView, "get_queryset", fail)
    response = staff_client.get(reverse("support:conversation-list"))

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected server error occurred."}
