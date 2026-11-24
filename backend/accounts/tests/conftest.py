from uuid import uuid4

import pytest
from django.core.cache import caches
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.roles import SUPPORT_AGENT_GROUP


@pytest.fixture(autouse=True)
def clear_login_attempts():
    caches["login_attempts"].clear()
    yield
    caches["login_attempts"].clear()


@pytest.fixture
def make_account(django_user_model, support_groups):
    def create(*roles, **flags):
        credentials = {"username": f"test-{uuid4().hex}", "password": str(uuid4())}
        account = django_user_model.objects.create_user(**credentials, **flags)
        account.groups.add(*(support_groups[name] for name in roles))
        return account, credentials

    return create


@pytest.fixture
def agent(make_account):
    return make_account(SUPPORT_AGENT_GROUP)


@pytest.fixture
def browser_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def signed_in(browser_client, agent):
    _, credentials = agent
    token = browser_client.get(reverse("accounts:csrf")).json()["csrfToken"]
    response = browser_client.post(
        reverse("accounts:login"), credentials, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 200
    token = browser_client.get(reverse("accounts:csrf")).json()["csrfToken"]
    return browser_client, token
