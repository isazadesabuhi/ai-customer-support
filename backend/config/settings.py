"""Runtime settings loaded by Django entry points."""

import os

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from .base_settings import *  # noqa: F403
from .browser import frontend_origins
from .database import postgres_database

debug_value = os.getenv("DJANGO_DEBUG", "false").strip().lower()
if debug_value not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be true or false.")

DEBUG = debug_value == "true"
local_development = os.getenv("DJANGO_ENV") == "development"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    if not local_development:
        raise ImproperlyConfigured(
            "Set a non-empty DJANGO_SECRET_KEY outside local development."
        )
    SECRET_KEY = get_random_secret_key()

allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not local_development
CORS_ALLOWED_ORIGINS = frontend_origins(
    os.getenv("DJANGO_FRONTEND_ORIGINS"), local_development=local_development
)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

DATABASES = {"default": postgres_database()}
