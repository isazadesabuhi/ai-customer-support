import re
from dataclasses import replace
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from config.database import TEST_DATABASE_NAME
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
from support.seed_data import inventory, operations
from support.seed_data.scenarios import CUSTOMERS, SCENARIOS


def test_dataset_coverage_and_relationships():
    rows = inventory.build_inventory()
    assert [len(rows[model]) for model in (Customer, Conversation, Message)] == [
        8,
        18,
        53,
    ]
    assert len({x.key for x in CUSTOMERS}) == len(CUSTOMERS)
    assert len({x.key for x in SCENARIOS}) == len(SCENARIOS)
    assert {scenario.category for scenario in SCENARIOS} == set(AnalysisCategory.values)
    assert {scenario.status for scenario in SCENARIOS} == set(ConversationStatus.values)
    assert {scenario.sentiment for scenario in SCENARIOS} == set(Sentiment.values)
    assert {scenario.urgency for scenario in SCENARIOS} == set(Urgency.values)
    assert sum(scenario.urgency == Urgency.HIGH for scenario in SCENARIOS) == 4
    assert sum(len(scenario.messages) == 1 for scenario in SCENARIOS) == 2
    assert {customer.email.split("@")[1] for customer in rows[Customer].values()} == {
        "example.com"
    }
    assert all(
        ticket.customer_id in rows[Customer] for ticket in rows[Conversation].values()
    )
    assert all(
        msg.conversation_id in rows[Conversation] for msg in rows[Message].values()
    )


def test_identifiers_and_timeline_are_deterministic():
    first = inventory.build_inventory()
    second = inventory.build_inventory()
    all_ids = {key for group in first.values() for key in group}
    assert len(all_ids) == sum(map(len, first.values()))
    assert {key.version for key in all_ids} == {5}

    for scenario in SCENARIOS:
        ticket_id = inventory.seed_id("conversation", scenario.key)
        ticket = first[Conversation][ticket_id]
        assert second[Conversation][ticket_id].created_at == ticket.created_at
        assert ticket.customer_id == inventory.seed_id(
            "customer", scenario.customer_key
        )
        messages = [
            msg for msg in first[Message].values() if msg.conversation_id == ticket.pk
        ]
        assert messages[0].sender == MessageSender.CUSTOMER
        assert messages[0].created_at == ticket.created_at
        assert messages[-1].created_at == ticket.updated_at
        assert all(
            earlier.created_at < later.created_at
            for earlier, later in zip(messages, messages[1:])
        )
        assert all(
            second[Message][msg.pk].created_at == msg.created_at for msg in messages
        )
        if ticket.status == ConversationStatus.RESOLVED:
            assert messages[-1].sender == MessageSender.AGENT


def test_authored_text_excludes_contact_and_secret_values():
    rows = inventory.build_inventory()
    content = "\n".join(
        [
            *(ticket.subject for ticket in rows[Conversation].values()),
            *(msg.content for msg in rows[Message].values()),
        ]
    )
    assert "@" not in content
    assert not re.search(r"\d(?:[- .]?\d){8,}", content)
    assert not re.search(
        r"\b(?:password|token|secret|api key)\s*[:=]", content, flags=re.I
    )
    assert not re.search(
        r"\b\d+\s+\w+\s+(?:street|st\.|avenue|ave\.|road|rd\.)\b", content, flags=re.I
    )


@pytest.mark.parametrize(
    "scenario, error",
    [
        (replace(SCENARIOS[0], customer_key="missing"), "unknown sample customer"),
        (
            replace(SCENARIOS[0], status="invalid"),
            "invalid sample conversation fields: status",
        ),
        (
            replace(SCENARIOS[0], messages=((1, MessageSender.CUSTOMER, "Late"),)),
            "start at zero",
        ),
        (
            replace(SCENARIOS[0], messages=((0, MessageSender.AGENT, "Too early"),)),
            "first sample message",
        ),
        (
            replace(SCENARIOS[0], messages=((0, "invalid", "Bad sender"),)),
            "first sample message",
        ),
        (
            replace(
                SCENARIOS[0],
                messages=(
                    (0, MessageSender.CUSTOMER, "hello"),
                    (5, "invalid", "reply"),
                ),
            ),
            "invalid sample message fields: sender",
        ),
    ],
)
def test_invalid_scenarios_are_rejected(monkeypatch, scenario, error):
    monkeypatch.setattr(inventory, "SCENARIOS", (scenario,))
    with pytest.raises(CommandError, match=f"(?i){error}"):
        inventory.build_inventory()


def test_duplicate_scenario_key_is_rejected(monkeypatch):
    monkeypatch.setattr(inventory, "SCENARIOS", (SCENARIOS[0], SCENARIOS[0]))
    with pytest.raises(CommandError, match="Duplicate sample key or UUID"):
        inventory.build_inventory()


def test_non_reserved_email_is_rejected(monkeypatch):
    monkeypatch.setattr(
        inventory,
        "CUSTOMERS",
        (replace(CUSTOMERS[0], email="fictional@email.invalid"),),
    )
    with pytest.raises(CommandError, match="reserved example domains"):
        inventory.build_inventory()


@pytest.mark.parametrize(
    "module, env, host, name",
    [
        ("config.settings", "production", "127.0.0.1", "support"),
        ("config.settings", None, "127.0.0.1", "support"),
        ("config.settings", "preview", "127.0.0.1", "support"),
        ("config.settings", "development", "database.example.com", "support"),
        ("config.settings", "development", "127.0.0.1", "postgres"),
        ("config.settings", "development", "127.0.0.1", TEST_DATABASE_NAME),
        ("config.postgres_test_settings", None, "127.0.0.1", "postgres"),
        ("config.test_settings", "development", "127.0.0.1", TEST_DATABASE_NAME),
    ],
)
@pytest.mark.parametrize(
    "options",
    [{}, {"clear": True}, {"dry_run": True}, {"clear": True, "dry_run": True}],
)
def test_disallowed_configuration_refuses_before_connection(
    monkeypatch, module, env, host, name, options
):
    database = SimpleNamespace(
        vendor="postgresql",
        settings_dict={"NAME": name, "HOST": host},
        ensure_connection=lambda: pytest.fail("Unsafe target was opened"),
    )
    monkeypatch.setattr(operations, "connection", database)
    with (
        override_settings(SETTINGS_MODULE=module, DJANGO_ENV=env, DEBUG=True),
        pytest.raises(CommandError, match="explicit loopback development"),
    ):
        call_command("seed_support_data", **options, skip_checks=True)


def test_reports_mismatched_connected_host(monkeypatch):
    database = SimpleNamespace(
        vendor="postgresql",
        settings_dict={"NAME": "support", "HOST": "127.0.0.1"},
        ensure_connection=lambda: None,
        connection=SimpleNamespace(
            info=SimpleNamespace(dbname="support", hostaddr="192.0.2.1")
        ),
    )
    monkeypatch.setattr(operations, "connection", database)
    with (
        override_settings(SETTINGS_MODULE="config.settings", DJANGO_ENV="development"),
        pytest.raises(
            CommandError, match="did not match the authorized local database"
        ),
    ):
        operations.require_seed_database()
