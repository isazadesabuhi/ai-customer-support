"""Protect, compare, and apply the development seed inventory."""

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection
from django.db.models.functions import Lower

from config.database import TEST_DATABASE_NAME
from support.models import AIAnalysis, Conversation, Customer, DraftResponse, Message

LOCAL_HOST = "127.0.0.1"


def require_seed_database():
    database = connection.settings_dict
    name = database["NAME"]
    local_development = (
        settings.SETTINGS_MODULE == "config.settings"
        and getattr(settings, "DJANGO_ENV", None) == "development"
        and name not in {"postgres", "template0", "template1", TEST_DATABASE_NAME}
    )
    isolated_test = (
        settings.SETTINGS_MODULE == "config.postgres_test_settings"
        and name == TEST_DATABASE_NAME
    )
    if not (
        name
        and connection.vendor == "postgresql"
        and database["HOST"] == LOCAL_HOST
        and (local_development or isolated_test)
    ):
        raise CommandError(
            "Sample data requires an explicit loopback development or isolated PostgreSQL test database."
        )

    connection.ensure_connection()
    info = connection.connection.info
    if info.hostaddr != LOCAL_HOST or info.dbname != name:
        raise CommandError(
            "The connected PostgreSQL target did not match the authorized local database."
        )


def find_owned_rows(inventory, *, lock):
    owned = {}
    for model, expected in inventory.items():
        rows = model.objects.filter(pk__in=expected).order_by("pk")
        if lock:
            rows = rows.select_for_update()
        owned[model] = set()
        for row in rows:
            record = expected[row.pk]
            if any(
                getattr(row, field.attname) != getattr(record, field.attname)
                for field in model._meta.concrete_fields
            ):
                raise CommandError(
                    f"Sample {model._meta.verbose_name} {row.pk} differs from the inventory. Nothing changed."
                )
            owned[model].add(row.pk)
    return owned


def find_missing_rows(inventory, owned):
    missing = {
        model: [
            record
            for identifier, record in records.items()
            if identifier not in owned[model]
        ]
        for model, records in inventory.items()
    }
    for customer in missing[Customer]:
        if (
            Customer.objects.alias(normalized_email=Lower("email"))
            .filter(normalized_email=customer.email)
            .exclude(pk=customer.pk)
            .exists()
        ):
            raise CommandError(
                "A sample email is already used by a different customer. Nothing changed."
            )
    return missing


def insert_missing_rows(missing):
    for model, records in missing.items():
        for record in records:
            record.full_clean()
            timestamps = {
                field.attname: getattr(record, field.attname)
                for field in model._meta.concrete_fields
                if getattr(field, "auto_now", False)
                or getattr(field, "auto_now_add", False)
            }
            record.save(force_insert=True)
            # Use an exact-PK update because auto_now_add and auto_now run on the insert.
            model.objects.filter(pk=record.pk).update(**timestamps)


def check_cleanup_relationships(owned):
    unexpected = (
        Conversation.objects.filter(customer_id__in=owned[Customer]).exclude(
            pk__in=owned[Conversation]
        ),
        Message.objects.filter(conversation_id__in=owned[Conversation]).exclude(
            pk__in=owned[Message]
        ),
        AIAnalysis.objects.filter(message_id__in=owned[Message]),
        DraftResponse.objects.filter(message_id__in=owned[Message]),
    )
    if any(rows.exists() for rows in unexpected):
        raise CommandError(
            "Sample cleanup would affect unrelated records. Nothing changed."
        )


def delete_owned_rows(owned):
    for model in (Message, Conversation, Customer):
        identifiers = owned[model]
        if identifiers:
            _, counts = model.objects.filter(pk__in=identifiers).delete()
            if counts != {model._meta.label: len(identifiers)}:
                raise CommandError(
                    "Sample cleanup detected an unexpected cascade. Nothing changed."
                )
