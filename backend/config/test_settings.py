"""Settings for pytest-django with an explicit test-only signing key."""

from .base_settings import *  # noqa: F403

SECRET_KEY = "test-only-signing-key"
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS = ["http://localhost:3000"]
