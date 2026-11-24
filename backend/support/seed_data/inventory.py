"""Build the complete ownership inventory without accessing the database."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

from support.models import (
    AnalysisCategory,
    Conversation,
    ConversationStatus,
    Customer,
    Message,
    MessageSender,
    Sentiment,
    Urgency,
)

from .scenarios import CUSTOMERS, SCENARIOS

SAMPLE_NAMESPACE = UUID("42041160-e7d3-4a8b-9502-f226b3301f65")
REFERENCE_TIME = datetime(2026, 11, 2, 9, tzinfo=UTC)
EXAMPLE_DOMAINS = {"example.com", "example.org", "example.net"}


def seed_id(kind, key):
    return uuid5(SAMPLE_NAMESPACE, f"{kind}:{key}")


def build_inventory():
    inventory = {Customer: {}, Conversation: {}, Message: {}}
    seen_ids = set()

    def register(record, *, exclude=()):
        if record.pk in seen_ids:
            raise CommandError(
                f"Duplicate sample key or UUID for {record._meta.verbose_name}."
            )
        try:
            # The definitions below validate references even when parents are absent in the DB.
            record.full_clean(
                exclude=exclude, validate_unique=False, validate_constraints=False
            )
        except ValidationError as exc:
            fields = ", ".join(exc.message_dict)
            raise CommandError(
                f"Invalid sample {record._meta.verbose_name} fields: {fields}."
            ) from None
        seen_ids.add(record.pk)
        inventory[type(record)][record.pk] = record

    emails = set()
    customer_time = REFERENCE_TIME - timedelta(days=14)
    for example in CUSTOMERS:
        customer = Customer(
            id=seed_id("customer", example.key),
            name=example.name,
            email=example.email,
            created_at=customer_time,
            updated_at=customer_time,
        )
        register(customer)
        if (
            customer.email.rsplit("@", 1)[-1] not in EXAMPLE_DOMAINS
            or customer.email in emails
        ):
            raise CommandError(
                "Sample customer emails must be unique and use reserved example domains."
            )
        emails.add(customer.email)

    for index, scenario in enumerate(SCENARIOS):
        customer_id = seed_id("customer", scenario.customer_key)
        if customer_id not in inventory[Customer]:
            raise CommandError(
                "A sample conversation references an unknown sample customer."
            )
        if (
            scenario.category not in AnalysisCategory.values
            or scenario.sentiment not in Sentiment.values
            or scenario.urgency not in Urgency.values
        ):
            raise CommandError("A sample conversation has invalid scenario metadata.")

        offsets = [offset for offset, _, _ in scenario.messages]
        if not offsets or offsets[0] != 0 or offsets != sorted(set(offsets)):
            raise CommandError(
                "Sample message times must start at zero and increase strictly."
            )
        if scenario.messages[0][1] != MessageSender.CUSTOMER:
            raise CommandError("The first sample message must come from the customer.")
        if (
            scenario.status == ConversationStatus.RESOLVED
            and scenario.messages[-1][1] != MessageSender.AGENT
        ):
            raise CommandError(
                "A resolved sample conversation must end with an agent response."
            )

        created_at = REFERENCE_TIME + timedelta(days=index)
        conversation = Conversation(
            id=seed_id("conversation", scenario.key),
            customer_id=customer_id,
            subject=scenario.subject,
            status=scenario.status,
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=offsets[-1]),
        )
        register(conversation, exclude=("customer",))

        for position, (offset, sender, content) in enumerate(
            scenario.messages, start=1
        ):
            message = Message(
                id=seed_id("message", f"{scenario.key}:{position}"),
                conversation_id=conversation.pk,
                sender=sender,
                content=content,
                created_at=created_at + timedelta(minutes=offset),
            )
            register(message, exclude=("conversation",))

    return inventory
