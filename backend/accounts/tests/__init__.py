import pytest
from django.conf import settings

postgres_account_tests = [
    pytest.mark.postgres,
    pytest.mark.django_db,
    pytest.mark.skipif(
        settings.SETTINGS_MODULE != "config.postgres_test_settings",
        reason="Account tests require the isolated PostgreSQL settings.",
    ),
]
