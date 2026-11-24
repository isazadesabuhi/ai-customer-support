from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from support.models import BODY_MAX_LENGTH, Conversation, Message

from . import postgres_model_tests

pytestmark = postgres_model_tests

LIST_URL = reverse("support:conversation-list")


@pytest.mark.parametrize(
    "field, value",
    [
        ("customer_id", None),
        ("customer_id", "bad-uuid"),
        ("customer_id", str(uuid4())),
        ("subject", None),
        ("subject", ""),
        ("subject", " \t\n"),
        ("subject", 123),
        ("subject", "x" * 256),
        ("status", "open"),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
        ("id", str(uuid4())),
        ("customer", {"name": "Replacement"}),
        ("unexpected", "value"),
    ],
)
def test_invalid_conversation_payload_does_not_create_record(
    agent_client, customer, field, value
):
    payload = {"customer_id": str(customer.pk), "subject": "Refund request"}
    if value is None:
        del payload[field]
    else:
        payload[field] = value

    response = agent_client.post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert field in response.json()
    assert not Conversation.objects.exists()


@pytest.mark.parametrize(
    "field, value",
    [
        ("sender", None),
        ("sender", ""),
        ("sender", "system"),
        ("sender", "customer"),
        ("sender", "unknown"),
        ("content", None),
        ("content", ""),
        ("content", " \n\t"),
        ("content", "x" * (BODY_MAX_LENGTH + 1)),
        ("content", 123),
        ("conversation_id", str(uuid4())),
        ("conversation", str(uuid4())),
        ("id", str(uuid4())),
        ("created_at", "2026-01-01T00:00:00Z"),
    ],
)
def test_invalid_message_payload_does_not_create_record(
    agent_client, conversation, field, value
):
    payload = {"sender": "agent", "content": "An agent reply"}
    if value is None:
        del payload[field]
    else:
        payload[field] = value

    response = agent_client.post(
        reverse("support:conversation-messages", args=[conversation.pk]),
        payload,
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()
    assert not Message.objects.exists()


def test_message_content_accepts_exact_limit(agent_client, conversation):
    response = agent_client.post(
        reverse("support:conversation-messages", args=[conversation.pk]),
        {"sender": "agent", "content": "x" * BODY_MAX_LENGTH},
        format="json",
    )

    assert response.status_code == 201
    assert len(response.json()["content"]) == BODY_MAX_LENGTH


def test_model_validation_errors_use_public_field_names_and_roll_back(
    agent_client, customer, monkeypatch
):
    def fail(self):
        Conversation.objects.create(customer=customer, subject="Should be rolled back")
        raise ValidationError({"customer": "Customer is unavailable."})

    monkeypatch.setattr(Conversation, "full_clean", fail)
    response = agent_client.post(
        LIST_URL,
        {"customer_id": str(customer.pk), "subject": "Refund request"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {"customer_id": ["Customer is unavailable."]}
    assert not Conversation.objects.exists()


@pytest.mark.parametrize(
    "query", ["status=", "status=unknown", "status=open&status=closed"]
)
def test_invalid_status_filter(agent_client, query):
    response = agent_client.get(f"{LIST_URL}?{query}")

    assert response.status_code == 400
    assert "status" in response.json()


@pytest.mark.parametrize("endpoint", ["conversation-list", "conversation-messages"])
@pytest.mark.parametrize(
    "field, query",
    [
        ("page_size", "page_size=0"),
        ("page_size", "page_size=-1"),
        ("page_size", "page_size=101"),
        ("page_size", "page_size=abc"),
        ("page_size", "page_size=1.5"),
        ("page_size", "page_size="),
        ("page_size", "page_size=1&page_size=2"),
        ("page", "page=0"),
        ("page", "page=-1"),
        ("page", "page=abc"),
        ("page", "page="),
        ("page", "page=1&page=2"),
        ("page", "page=2"),
    ],
)
def test_invalid_pagination(agent_client, conversation, endpoint, field, query):
    args = [conversation.pk] if endpoint == "conversation-messages" else []
    url = reverse(f"support:{endpoint}", args=args)
    response = agent_client.get(f"{url}?{query}")

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize(
    "body, key", [("[1]", "non_field_errors"), ('{"subject":', "detail")]
)
def test_malformed_or_wrong_shape_json(agent_client, body, key):
    response = agent_client.post(LIST_URL, body, content_type="application/json")

    assert response.status_code == 400
    assert key in response.json()
    assert not Conversation.objects.exists()
