from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from support.models import BODY_MAX_LENGTH, Message, MessageSender

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_conversation_messages_use_timestamps_and_uuid_to_break_ties(conversation):
    earlier = Message.objects.create(
        conversation=conversation, sender=MessageSender.AGENT, content="I can help."
    )
    messages = [
        Message(
            id=UUID(int=number),
            conversation=conversation,
            sender=MessageSender.CUSTOMER,
            content="Private customer message",
        )
        for number in (2, 1)
    ]
    for message in messages:
        message.full_clean()
        message.save()
    first = earlier.created_at - timedelta(hours=1)
    Message.objects.filter(pk=earlier.pk).update(created_at=first)
    Message.objects.filter(pk__in=[message.pk for message in messages]).update(
        created_at=earlier.created_at
    )

    assert list(conversation.messages.all()) == [earlier, messages[1], messages[0]]
    assert timezone.is_aware(messages[0].created_at)
    assert str(messages[0]) == f"customer message {messages[0].pk}"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content", ""),
        ("content", " \t\n"),
        ("content", "x" * (BODY_MAX_LENGTH + 1)),
        ("sender", "ai"),
        ("conversation_id", uuid4()),
    ],
)
def test_message_rejects_invalid_values(conversation, field, value):
    values = {
        "conversation_id": conversation.pk,
        "sender": MessageSender.CUSTOMER,
        "content": "Valid body",
        field: value,
    }
    with pytest.raises(ValidationError) as error:
        Message(**values).full_clean()

    assert field.removesuffix("_id") in error.value.message_dict


def test_deleting_conversation_cascades_to_messages(message):
    message.conversation.delete()

    assert not Message.objects.filter(pk=message.pk).exists()
