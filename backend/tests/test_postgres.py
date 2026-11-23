import pytest
from django.conf import settings
from django.db import connection

from config.database import TEST_DATABASE_NAME

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        settings.SETTINGS_MODULE != "config.postgres_test_settings",
        reason="Use --ds=config.postgres_test_settings with the local PostgreSQL service.",
    ),
]


@pytest.mark.django_db
def test_query_runs_as_non_superuser_in_the_isolated_postgres_database():
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1, current_database(), rolsuper FROM pg_roles WHERE rolname = current_user"
        )
        assert cursor.fetchone() == (1, TEST_DATABASE_NAME, False)
