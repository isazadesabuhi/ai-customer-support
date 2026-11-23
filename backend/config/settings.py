"""Runtime settings loaded by Django entry points."""

import os

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from .base_settings import *  # noqa: F403
from .database import postgres_database

debug_value = os.getenv("DJANGO_DEBUG", "false").strip().lower()
if debug_value not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be true or false.")

DEBUG = debug_value == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    if os.getenv("DJANGO_ENV") != "development":
        raise ImproperlyConfigured(
            "Set a non-empty DJANGO_SECRET_KEY outside local development."
        )
    SECRET_KEY = get_random_secret_key()

allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

DATABASES = {"default": postgres_database()}
