from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from support.models import Conversation, Customer, Message
from support.seed_data.inventory import build_inventory
from support.seed_data.operations import (
    check_cleanup_relationships,
    delete_owned_rows,
    find_missing_rows,
    find_owned_rows,
    insert_missing_rows,
    require_seed_database,
)


class Command(BaseCommand):
    help = "Seed or clear the fictional support dataset in the local development or test database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview changes without writing."
        )
        parser.add_argument(
            "--clear", action="store_true", help="Delete verified fictional records."
        )

    def handle(self, *args, clear, dry_run, **options):
        try:
            require_seed_database()
            inventory = build_inventory()
            with transaction.atomic():
                owned = find_owned_rows(inventory, lock=not dry_run)
                if clear:
                    check_cleanup_relationships(owned)
                    if not dry_run:
                        delete_owned_rows(owned)
                    affected = owned
                else:
                    affected = find_missing_rows(inventory, owned)
                    if not dry_run:
                        insert_missing_rows(affected)
        except (DatabaseError, ValidationError):
            raise CommandError(
                "Sample data operation rolled back. Check database readiness, migrations, and conflicts."
            ) from None

        if dry_run:
            self.stdout.write("Sample data dry run. No records changed.")
        else:
            self.stdout.write(self.style.SUCCESS("Sample data operation completed."))
        action = "deleted" if clear else "created"
        if dry_run:
            action = f"would be {action}"
        for model, label in (
            (Customer, "Customers"),
            (Conversation, "Conversations"),
            (Message, "Messages"),
        ):
            self.stdout.write(f"{label} {action}: {len(affected[model])}")
        if not clear:
            self.stdout.write(
                f"Existing sample records reused: {sum(map(len, owned.values()))}"
            )
