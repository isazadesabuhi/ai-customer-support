"""Validate PostgreSQL settings supplied through the process environment."""

import os
import re

from django.core.exceptions import ImproperlyConfigured

TEST_DATABASE_NAME = "test_ai_customer_support"


def postgres_database() -> dict:
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    values = {name: os.getenv(name, "") for name in required}
    missing = [name for name, value in values.items() if not value.strip()]
    if missing:
        raise ImproperlyConfigured(
            f"Set non-empty PostgreSQL variables: {', '.join(missing)}."
        )

    database_name = values["POSTGRES_DB"].strip()
    if database_name in {"postgres", "template0", "template1", TEST_DATABASE_NAME}:
        raise ImproperlyConfigured(
            "POSTGRES_DB cannot use a reserved system or test database name."
        )

    host = os.getenv("DB_HOST", "127.0.0.1").strip()
    if not host:
        raise ImproperlyConfigured("DB_HOST must be non-empty.")

    port = os.getenv("DB_PORT", "5432").strip()
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
        raise ImproperlyConfigured("DB_PORT must be a whole number from 1 to 65535.")

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": values["POSTGRES_USER"].strip(),
        "PASSWORD": values["POSTGRES_PASSWORD"],
        "HOST": host,
        "PORT": int(port),
        "OPTIONS": {"connect_timeout": 5},
    }
