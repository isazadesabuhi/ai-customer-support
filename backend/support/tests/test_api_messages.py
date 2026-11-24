from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from django.urls import reverse
from django.utils import timezone

from support.models import AIAnalysis, Conversation, DraftResponse, Message

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_empty_message_list(staff_client, conversation):
    response = staff_client.get(
        reverse("support:conversation-messages", args=[conversation.pk])
    )

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_messages_are_paginated_chronologically_and_scoped(staff_client, conversation):
    url = reverse("support:conversation-messages", args=[conversation.pk])
    other = Conversation.objects.create(
        customer=conversation.customer, subject="Unrelated"
    )
    Message.objects.create(
        conversation=other, sender="customer", content="Private other message"
    )
    for number, sender in enumerate(("customer", "agent", "system"), start=1):
        Message.objects.create(
            id=UUID(int=number),
            conversation=conversation,
            sender=sender,
            content=f"Message {number}",
        )
    now = timezone.now()
    conversation.messages.update(created_at=now)
    conversation.messages.filter(pk=UUID(int=3)).update(
        created_at=now - timedelta(days=1)
    )
    AIAnalysis.objects.create(
        message_id=UUID(int=1),
        category="general",
        sentiment="neutral",
        urgency="normal",
        model_name="example",
        reason="Private analysis",
    )
    DraftResponse.objects.create(message_id=UUID(int=1), content="Private draft")

    response = staff_client.get(url, {"page_size": 2})
    assert response.status_code == 200
    first = response.json()
    assert first["count"] == 3
    assert [item["id"] for item in first["results"]] == [
        str(UUID(int=n)) for n in (3, 1)
    ]
    assert [item["sender"] for item in first["results"]] == ["system", "customer"]
    assert all(
        set(item) == {"id", "sender", "content", "created_at"}
        for item in first["results"]
    )
    assert parse_qs(urlsplit(first["next"]).query) == {
        "page": ["2"],
        "page_size": ["2"],
    }
    second = staff_client.get(url, {"page": 2, "page_size": 2}).json()
    assert [item["id"] for item in second["results"]] == [str(UUID(int=2))]
    assert second["next"] is None


def test_create_adds_agent_message_without_changing_conversation(
    staff_client, conversation
):
    Conversation.objects.filter(pk=conversation.pk).update(status="pending")
    url = reverse("support:conversation-messages", args=[conversation.pk])
    content = "  Could you provide your order number?\nThank you.\n"
    response = staff_client.post(
        url, {"sender": "agent", "content": content}, format="json"
    )

    assert response.status_code == 201
    data = response.json()
    created = Message.objects.get(pk=data["id"])
    assert created.conversation == conversation
    assert created.sender == "agent"
    assert created.content == content
    assert set(data) == {"id", "sender", "content", "created_at"}
    assert staff_client.get(url).json()["results"] == [data]
    conversation.refresh_from_db()
    assert conversation.status == "pending"


def test_message_list_query_count_stays_bounded(
    staff_client, conversation, django_assert_max_num_queries
):
    Message.objects.bulk_create(
        [
            Message(conversation=conversation, sender="agent", content=f"Reply {n}")
            for n in range(5)
        ]
    )

    with django_assert_max_num_queries(4):
        response = staff_client.get(
            reverse("support:conversation-messages", args=[conversation.pk])
        )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 5
