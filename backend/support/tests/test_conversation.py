from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from support.models import Conversation, ConversationStatus

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_customer_has_many_conversations_in_newest_first_order(
    customer, conversation, monkeypatch
):
    later = Conversation(customer=customer, subject="Another order")
    later.full_clean()
    later.save()
    earlier = conversation.created_at - timedelta(hours=1)
    Conversation.objects.filter(pk=conversation.pk).update(created_at=earlier)

    assert conversation.status == ConversationStatus.OPEN
    assert list(customer.conversations.all()) == [later, conversation]
    assert timezone.is_aware(later.created_at)
    assert later.updated_at >= later.created_at
    assert str(later) == f"Another order ({later.pk})"

    updated_at = later.updated_at + timedelta(seconds=1)
    monkeypatch.setattr(timezone, "now", lambda: updated_at)
    later.status = ConversationStatus.PENDING
    later.save()
    later.refresh_from_db()
    assert later.updated_at == updated_at
    assert later.status == ConversationStatus.PENDING


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject", ""),
        ("subject", " \t "),
        ("subject", "a" * 256),
        ("status", "invalid"),
        ("customer_id", None),
        ("customer_id", uuid4()),
    ],
)
def test_conversation_rejects_invalid_values(customer, field, value):
    values = {"customer_id": customer.pk, "subject": "Valid subject", field: value}
    with pytest.raises(ValidationError) as error:
        Conversation(**values).full_clean()

    assert field.removesuffix("_id") in error.value.message_dict


def test_referenced_customer_is_protected(conversation):
    with pytest.raises(ProtectedError):
        conversation.customer.delete()

    assert Conversation.objects.filter(pk=conversation.pk).exists()
