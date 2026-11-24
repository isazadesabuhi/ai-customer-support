from io import StringIO

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.roles import SUPPORT_AGENT_GROUP, SUPPORT_GROUPS, SUPPORT_PERMISSIONS

from . import postgres_account_tests

pytestmark = postgres_account_tests


def test_role_provisioning_is_idempotent_and_preserves_unrelated_groups_and_users(
    django_user_model,
):
    user = django_user_model.objects.create_user(
        username="existing-account", is_staff=True
    )
    unrelated = Group.objects.create(name="Other group")
    unrelated_permission = Permission.objects.get(
        content_type__app_label="auth", codename="view_user"
    )
    unrelated.permissions.add(unrelated_permission)
    user.groups.add(unrelated)

    call_command("provision_support_roles", stdout=StringIO())
    ids = dict(Group.objects.values_list("name", "pk"))
    Group.objects.get(name=SUPPORT_AGENT_GROUP).permissions.add(unrelated_permission)
    call_command("provision_support_roles", stdout=StringIO())

    assert dict(Group.objects.values_list("name", "pk")) == ids
    assert set(ids) == {*SUPPORT_GROUPS, unrelated.name}
    for group in Group.objects.filter(name__in=SUPPORT_GROUPS):
        assert set(
            f"{label}.{code}"
            for label, code in group.permissions.values_list(
                "content_type__app_label", "codename"
            )
        ) == set(SUPPORT_PERMISSIONS)
    assert list(unrelated.permissions.all()) == [unrelated_permission]
    assert list(user.groups.all()) == [unrelated]
    user.refresh_from_db()
    assert user.is_staff and not user.is_superuser
    assert django_user_model.objects.count() == 1


def test_provisioning_requires_django_model_permissions():
    Permission.objects.filter(
        content_type__app_label="support", codename="view_message"
    ).delete()

    with pytest.raises(CommandError, match="Run Django migrate first"):
        call_command("provision_support_roles", stdout=StringIO())

    assert not Group.objects.filter(name__in=SUPPORT_GROUPS).exists()
