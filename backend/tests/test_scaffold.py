from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks


def test_project_configuration_loads():
    assert settings.ROOT_URLCONF == "config.urls"
    assert apps.is_installed("rest_framework")


def test_django_system_checks_report_no_issues():
    assert run_checks() == []


def test_unconfigured_root_returns_not_found(client):
    response = client.get("/")

    assert response.status_code == 404
