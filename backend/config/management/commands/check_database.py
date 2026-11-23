"""Check authorization and readiness with a read-only PostgreSQL query."""

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection


class Command(BaseCommand):
    help = "Check the configured PostgreSQL database with a read-only query."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("The configured database backend must be PostgreSQL.")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
        except DatabaseError:
            raise CommandError(
                "PostgreSQL query failed. Check service readiness and the database "
                "name, role, password, host, and port."
            ) from None

        if result != (1,):
            raise CommandError("PostgreSQL returned an unexpected result for SELECT 1.")

        self.stdout.write(
            self.style.SUCCESS("PostgreSQL connection and query succeeded.")
        )
