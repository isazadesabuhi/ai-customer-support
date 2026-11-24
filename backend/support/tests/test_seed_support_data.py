import re
from dataclasses import replace
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection
from django.db.models import QuerySet
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.roles import SUPPORT_AGENT_GROUP, SUPPORT_MANAGER_GROUP
from support.models import AIAnalysis, Conversation, Customer, DraftResponse, Message
from support.seed_data import inventory
from support.seed_data.scenarios import CUSTOMERS, SCENARIOS

from . import postgres_model_tests

pytestmark = postgres_model_tests


def run_seed(**options):
    out = StringIO()
    call_command("seed_support_data", stdout=out, **options)
    return out.getvalue()


def snapshot():
    return {
        model: list(model.objects.order_by("pk").values())
        for model in (Customer, Conversation, Message, AIAnalysis, DraftResponse)
    }


@pytest.fixture
def seeded():
    run_seed()
    return inventory.build_inventory()


def test_initial_seed_persists_valid_inventory_and_timestamps():
    report = run_seed()
    expected = inventory.build_inventory()
    assert "Customers created: 8" in report
    assert "Conversations created: 18" in report
    assert "Messages created: 53" in report

    for model, records in expected.items():
        assert set(model.objects.values_list("pk", flat=True)) == records.keys()
        for row in model.objects.all():
            original = records[row.pk]
            assert all(
                getattr(row, field.attname) == getattr(original, field.attname)
                for field in model._meta.concrete_fields
            )

    for ticket in Conversation.objects.prefetch_related("messages"):
        assert list(ticket.messages.values_list("created_at", flat=True)) == sorted(
            record.created_at
            for record in expected[Message].values()
            if record.conversation_id == ticket.pk
        )
    assert not AIAnalysis.objects.exists()
    assert not DraftResponse.objects.exists()


def test_seed_twice_preserves_exact_rows_and_unrelated_data(seeded, message):
    before = snapshot()
    report = run_seed()

    assert "Customers created: 0" in report
    assert "Conversations created: 0" in report
    assert "Messages created: 0" in report
    assert "Existing sample records reused: 79" in report
    assert snapshot() == before


def test_seed_restores_a_missing_row_with_its_original_id_and_timestamp(seeded):
    last_message = Message.objects.latest("created_at")
    message_id = last_message.pk
    timestamp = last_message.created_at
    last_message.delete()

    assert "Messages created: 1" in run_seed()
    assert Message.objects.get(pk=message_id).created_at == timestamp


@pytest.mark.parametrize("clear", [False, True])
def test_dry_run_plans_actual_changes_with_only_reads(clear):
    if clear:
        run_seed()
    before = snapshot()
    with CaptureQueriesContext(connection) as queries:
        output = run_seed(clear=clear, dry_run=True)

    action = "deleted" if clear else "created"
    assert f"Customers would be {action}: 8" in output
    assert f"Conversations would be {action}: 18" in output
    assert f"Messages would be {action}: 53" in output
    assert snapshot() == before
    for query in queries:
        assert not re.search(
            r"^\s*(?:INSERT|UPDATE|DELETE|TRUNCATE)\b|\bFOR UPDATE\b",
            query["sql"],
            flags=re.I,
        )


@pytest.mark.parametrize("dry_run", [False, True])
def test_case_insensitive_email_collision_is_not_adopted(dry_run):
    Customer.objects.create(name="Unrelated", email=CUSTOMERS[-1].email.upper())
    before = snapshot()

    with pytest.raises(CommandError, match="sample email is already used"):
        run_seed(dry_run=dry_run)

    assert snapshot() == before


def test_reserved_uuid_collision_blocks_seed_and_cleanup():
    Customer.objects.create(
        id=inventory.seed_id("customer", CUSTOMERS[-1].key),
        name="Unrelated",
        email="unrelated@example.com",
    )
    before = snapshot()

    for clear in (False, True):
        with pytest.raises(CommandError, match="differs from the inventory"):
            run_seed(clear=clear)
    assert snapshot() == before


@pytest.mark.parametrize(
    "record_source, patch",
    [("CUSTOMERS", {"name": " "}), ("SCENARIOS", {"customer_key": "unknown"})],
)
def test_invalid_data_leaves_no_partial_records(monkeypatch, record_source, patch):
    records = getattr(inventory, record_source)
    monkeypatch.setattr(
        inventory, record_source, (*records[:-1], replace(records[-1], **patch))
    )

    with pytest.raises(CommandError):
        run_seed()

    assert not any(snapshot().values())


def test_message_insert_failure_rolls_back_earlier_writes(monkeypatch):
    original_save = Message.save
    last_message = max(
        inventory.build_inventory()[Message].values(), key=lambda msg: msg.created_at
    )

    def fail_final_message(self, *args, **kwargs):
        if self.pk == last_message.pk:
            assert Customer.objects.count() == 8
            assert Conversation.objects.count() == 18
            assert Message.objects.count() == 52
            raise IntegrityError("Private test database diagnostic")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(Message, "save", fail_final_message)
    with pytest.raises(CommandError, match="rolled back") as error:
        run_seed()

    assert "Private test" not in str(error.value)
    assert not any(snapshot().values())


def test_clear_preserves_unrelated_records_and_repeating_clear_is_safe(message):
    AIAnalysis.objects.create(
        message=message,
        category="general",
        sentiment="neutral",
        urgency="low",
        model_name="test",
    )
    DraftResponse.objects.create(message=message, content="Unrelated draft")
    before = snapshot()
    run_seed()

    report = run_seed(clear=True)
    assert "Customers deleted: 8" in report
    assert "Conversations deleted: 18" in report
    assert "Messages deleted: 53" in report
    assert snapshot() == before
    assert "Customers deleted: 0" in run_seed(clear=True)
    assert snapshot() == before


@pytest.mark.parametrize("related", ["conversation", "message", "analysis", "draft"])
def test_cleanup_refuses_unexpected_related_rows(seeded, related):
    ticket = Conversation.objects.get(pk=next(iter(seeded[Conversation])))
    message = ticket.messages.first()
    if related == "conversation":
        Conversation.objects.create(
            customer=ticket.customer, subject="Unrelated ticket"
        )
    elif related == "message":
        Message.objects.create(
            conversation=ticket, sender="agent", content="Manually added reply"
        )
    elif related == "analysis":
        AIAnalysis.objects.create(
            message=message,
            category="shipping",
            sentiment="neutral",
            urgency="low",
            model_name="test",
        )
    else:
        DraftResponse.objects.create(message=message, content="Manually added draft")
    before = snapshot()

    for dry_run in (False, True):
        with pytest.raises(CommandError, match="would affect unrelated records"):
            run_seed(clear=True, dry_run=dry_run)
    assert snapshot() == before
    assert "Existing sample records reused: 79" in run_seed()
    assert snapshot() == before


@pytest.mark.parametrize(
    "model, modification",
    [
        (Customer, {"name": "Edited name"}),
        (Conversation, {"status": "closed"}),
        (Message, {"content": "Edited reply"}),
    ],
)
def test_existing_edits_refuse_both_seed_and_clear(seeded, model, modification):
    model.objects.filter(pk=next(iter(seeded[model]))).update(**modification)
    before = snapshot()

    with pytest.raises(CommandError, match="differs from the inventory"):
        run_seed()
    with pytest.raises(CommandError, match="differs from the inventory"):
        run_seed(clear=True)

    assert snapshot() == before


def test_cleanup_rolls_back_if_a_delete_fails_after_message_removal(
    seeded, monkeypatch
):
    before = snapshot()
    original_delete = QuerySet.delete

    def fail_conversation_delete(self):
        if self.model is Conversation:
            assert Message.objects.count() == 0
            raise IntegrityError("Synthetic failure after deleting messages")
        return original_delete(self)

    monkeypatch.setattr(QuerySet, "delete", fail_conversation_delete)
    with pytest.raises(CommandError, match="rolled back"):
        run_seed(clear=True)

    assert snapshot() == before


@pytest.mark.parametrize("role", [SUPPORT_AGENT_GROUP, SUPPORT_MANAGER_GROUP])
def test_seeded_api_endpoints_keep_roles_pagination_filters_and_ordering(
    seeded, django_user_model, support_groups, role
):
    user = django_user_model.objects.create_user(username="seed-api-reader")
    user.groups.add(support_groups[role])
    client = APIClient()
    client.force_login(user)
    list_url = reverse("support:conversation-list")
    response = client.get(list_url, {"status": "open", "page_size": 2})
    assert response.status_code == 200
    open_tickets = list(Conversation.objects.filter(status="open"))
    page = response.json()
    assert page["count"] == 6
    assert [entry["id"] for entry in page["results"]] == [
        str(ticket.pk) for ticket in open_tickets[:2]
    ]
    assert page["next"]
    second = client.get(list_url, {"status": "open", "page_size": 2, "page": 2})
    assert second.status_code == 200
    assert [entry["id"] for entry in second.json()["results"]] == [
        str(ticket.pk) for ticket in open_tickets[2:4]
    ]

    target = inventory.seed_id("conversation", SCENARIOS[0].key)
    detail = client.get(reverse("support:conversation-detail", args=[target]))
    assert detail.status_code == 200
    assert detail.json()["subject"] == SCENARIOS[0].subject
    timeline = client.get(reverse("support:conversation-messages", args=[target]))
    assert timeline.status_code == 200
    assert [entry["content"] for entry in timeline.json()["results"]] == [
        message[2] for message in SCENARIOS[0].messages
    ]


@pytest.mark.parametrize("signed_in", [False, True])
def test_seeded_api_is_private_for_anonymous_and_unassigned_users(
    seeded, reviewer, signed_in
):
    target = next(iter(seeded[Conversation]))
    client = APIClient()
    if signed_in:
        client.force_login(reviewer)
    for route, args in (
        ("conversation-list", []),
        ("conversation-detail", [target]),
        ("conversation-messages", [target]),
    ):
        response = client.get(reverse(f"support:{route}", args=args))
        assert response.status_code == 403
        assert set(response.json()) == {"detail"}
