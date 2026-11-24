from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from support.models import (
    AIAnalysis,
    AnalysisCategory,
    Conversation,
    Customer,
    DraftResponse,
    DraftStatus,
    Message,
    MessageSender,
    Sentiment,
    Urgency,
)

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_postgresql_rejects_case_insensitive_duplicate_emails(customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Customer.objects.create(name="Other Customer", email="CUSTOMER@EXAMPLE.TEST")


@pytest.mark.parametrize(
    "confidence", [-0.1, 1.1, float("nan"), float("inf"), float("-inf")]
)
def test_postgresql_rejects_invalid_confidence(message, confidence):
    with pytest.raises(IntegrityError), transaction.atomic():
        AIAnalysis.objects.create(
            message=message,
            category=AnalysisCategory.GENERAL,
            sentiment=Sentiment.NEUTRAL,
            urgency=Urgency.NORMAL,
            confidence=confidence,
            model_name="example/model",
        )


def test_postgresql_allows_only_one_analysis_per_message(message):
    values = {
        "message": message,
        "category": AnalysisCategory.GENERAL,
        "sentiment": Sentiment.NEUTRAL,
        "urgency": Urgency.NORMAL,
        "model_name": "example/model",
    }
    AIAnalysis.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        AIAnalysis.objects.create(**values)


@pytest.mark.parametrize(
    ("status", "has_reviewer", "has_timestamp"),
    [
        (DraftStatus.PENDING, True, False),
        (DraftStatus.PENDING, False, True),
        (DraftStatus.APPROVED, False, False),
        (DraftStatus.APPROVED, True, False),
        (DraftStatus.REJECTED, False, True),
        ("invalid", False, False),
    ],
)
def test_postgresql_rejects_invalid_review_rows(
    message, reviewer, status, has_reviewer, has_timestamp
):
    with pytest.raises(IntegrityError), transaction.atomic():
        DraftResponse.objects.create(
            message=message,
            content="Proposal",
            status=status,
            reviewed_by=reviewer if has_reviewer else None,
            reviewed_at=timezone.now() if has_timestamp else None,
        )


@pytest.mark.parametrize("field", ["status", "subject"])
def test_postgresql_rejects_invalid_conversation_updates(conversation, field):
    value = "invalid" if field == "status" else " \t "
    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.filter(pk=conversation.pk).update(**{field: value})


def test_postgresql_rejects_missing_foreign_key():
    with pytest.raises(IntegrityError), transaction.atomic():
        Message.objects.create(
            conversation_id=uuid4(),
            sender=MessageSender.CUSTOMER,
            content="Orphan message",
        )
        connection.check_constraints(table_names=[Message._meta.db_table])


@pytest.mark.parametrize(
    ("model", "name", "columns"),
    [
        (Conversation, "support_conv_status_created", ["status", "created_at", "id"]),
        (
            Conversation,
            "support_conv_cust_created",
            ["customer_id", "created_at", "id"],
        ),
        (Message, "support_msg_conv_created", ["conversation_id", "created_at", "id"]),
        (
            DraftResponse,
            "support_draft_msg_created",
            ["message_id", "created_at", "id"],
        ),
        (DraftResponse, "support_draft_pending_created", ["created_at", "id"]),
    ],
)
def test_postgresql_schema_has_query_indexes(model, name, columns):
    with connection.cursor() as cursor:
        indexes = connection.introspection.get_constraints(cursor, model._meta.db_table)
        assert indexes[name]["index"]
        assert indexes[name]["columns"] == columns

        if name == "support_draft_pending_created":
            # Django's B-tree introspection omits this index's predicate.
            cursor.execute("SELECT pg_get_indexdef(%s::regclass)", [name])
            definition = cursor.fetchone()[0]
            assert "WHERE" in definition
            assert "'pending'" in definition
