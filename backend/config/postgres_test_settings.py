"""Explicit opt-in settings for isolated PostgreSQL integration tests."""

from django.core.exceptions import ImproperlyConfigured

from .database import TEST_DATABASE_NAME, postgres_database
from .test_settings import *  # noqa: F403

database = postgres_database()
if database["HOST"] != "127.0.0.1":
    raise ImproperlyConfigured("PostgreSQL tests require DB_HOST=127.0.0.1.")

# Start in the maintenance database and let Django create and drop only the
# dedicated test database. The configured development database is never opened.
DATABASES = {
    "default": {
        **database,
        "NAME": "postgres",
        "OPTIONS": {**database["OPTIONS"], "hostaddr": "127.0.0.1"},
        "TEST": {"NAME": TEST_DATABASE_NAME},
    },
}
