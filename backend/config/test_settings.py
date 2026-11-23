"""Settings for pytest-django with an explicit test-only signing key."""

from .base_settings import *  # noqa: F403

SECRET_KEY = "test-only-signing-key"
