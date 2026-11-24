from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from django.urls import reverse
from django.utils import timezone

from support.models import Conversation, ConversationStatus, Customer

from . import postgres_model_tests

pytestmark = postgres_model_tests

LIST_URL = reverse("support:conversation-list")


def test_empty_conversation_list(agent_client):
    response = agent_client.get(LIST_URL)

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_list_and_detail_share_public_schema(agent_client, message):
    conversation = message.conversation
    customer = conversation.customer
    listing = agent_client.get(LIST_URL)
    detail = agent_client.get(
        reverse("support:conversation-detail", args=[conversation.pk])
    )

    assert listing.status_code == detail.status_code == 200
    data = detail.json()
    assert listing.json()["results"] == [data]
    assert set(data) == {
        "id",
        "subject",
        "status",
        "customer",
        "created_at",
        "updated_at",
    }
    assert data["id"] == str(conversation.pk)
    assert data["subject"] == conversation.subject
    assert data["status"] == "open"
    assert data["customer"] == {
        "id": str(customer.pk),
        "name": customer.name,
        "email": customer.email,
    }
    assert data["created_at"].endswith("Z")
    assert data["updated_at"].endswith("Z")
    assert "no-store" in detail.headers["Cache-Control"]
    assert "private" in detail.headers["Cache-Control"]


def test_create_conversation_uses_existing_customer_and_default(agent_client, customer):
    response = agent_client.post(
        LIST_URL,
        {"customer_id": str(customer.pk), "subject": "Refund request"},
        format="json",
    )

    assert response.status_code == 201
    created = Conversation.objects.get(pk=response.json()["id"])
    assert created.subject == "Refund request"
    assert created.customer == customer
    assert created.status == ConversationStatus.OPEN
    assert Customer.objects.count() == 1
    assert (
        response.json()
        == agent_client.get(
            reverse("support:conversation-detail", args=[created.pk])
        ).json()
    )


@pytest.mark.parametrize("status", ConversationStatus.values)
def test_conversation_status_filter(agent_client, customer, status):
    conversations = {
        value: Conversation.objects.create(
            customer=customer, subject=value, status=value
        )
        for value in ConversationStatus.values
    }

    response = agent_client.get(LIST_URL, {"status": status})

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(conversations[status].pk)


def test_conversation_order_and_pagination(agent_client, customer):
    Conversation.objects.bulk_create(
        [
            Conversation(id=UUID(int=n), customer=customer, subject=f"Ticket {n}")
            for n in range(1, 22)
        ]
    )
    now = timezone.now()
    Conversation.objects.update(created_at=now)
    Conversation.objects.filter(pk=UUID(int=21)).update(
        created_at=now - timedelta(days=1)
    )

    first = agent_client.get(LIST_URL).json()
    assert first["count"] == 21
    assert [item["id"] for item in first["results"]] == [
        str(UUID(int=n)) for n in range(20, 0, -1)
    ]
    assert first["previous"] is None
    assert parse_qs(urlsplit(first["next"]).query) == {"page": ["2"]}
    second = agent_client.get(
        LIST_URL, {"status": "open", "page": 2, "page_size": 2}
    ).json()
    assert [item["id"] for item in second["results"]] == [
        str(UUID(int=n)) for n in (18, 17)
    ]
    assert parse_qs(urlsplit(second["previous"]).query) == {
        "status": ["open"],
        "page_size": ["2"],
    }
    assert parse_qs(urlsplit(second["next"]).query) == {
        "page": ["3"],
        "page_size": ["2"],
        "status": ["open"],
    }
    largest = agent_client.get(LIST_URL, {"page_size": 100})
    assert largest.status_code == 200
    assert len(largest.json()["results"]) == 21


def test_conversation_list_query_count_stays_bounded(
    agent_client, django_assert_max_num_queries
):
    for number in range(5):
        customer = Customer.objects.create(
            name=f"Customer {number}", email=f"c{number}@example.test"
        )
        Conversation.objects.create(customer=customer, subject=f"Ticket {number}")

    # Allow three fixed authorization queries for a fresh ordinary user.
    with django_assert_max_num_queries(6):
        response = agent_client.get(LIST_URL)

    assert response.status_code == 200
    assert len(response.json()["results"]) == 5
