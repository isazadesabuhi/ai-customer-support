import pytest

from support.models import Conversation, Customer, Message, MessageSender


@pytest.fixture
def customer():
    return Customer.objects.create(
        name="Example Customer", email="customer@example.test"
    )


@pytest.fixture
def conversation(customer):
    return Conversation.objects.create(customer=customer, subject="Order question")


@pytest.fixture
def message(conversation):
    return Message.objects.create(
        conversation=conversation,
        sender=MessageSender.CUSTOMER,
        content="Where is my order?",
    )


@pytest.fixture
def reviewer(django_user_model):
    return django_user_model.objects.create_user(username="support-reviewer")
