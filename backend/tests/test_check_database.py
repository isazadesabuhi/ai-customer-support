from io import StringIO
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError

from config.management.commands import check_database


def test_database_check_executes_a_read_only_query(monkeypatch):
    database = MagicMock(vendor="postgresql")
    cursor = database.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)
    monkeypatch.setattr(check_database, "connection", database)
    stdout = StringIO()

    call_command("check_database", stdout=stdout)

    cursor.execute.assert_called_once_with("SELECT 1")
    assert "PostgreSQL connection and query succeeded." in stdout.getvalue()


def test_database_check_sanitizes_driver_errors(monkeypatch):
    database = MagicMock(vendor="postgresql")
    database.cursor.side_effect = OperationalError(
        "driver details: private-test-marker"
    )
    monkeypatch.setattr(check_database, "connection", database)

    with pytest.raises(CommandError, match="PostgreSQL query failed") as error:
        call_command("check_database")

    assert "private-test-marker" not in str(error.value)
    assert error.value.__suppress_context__
