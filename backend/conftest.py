from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.roles import SUPPORT_GROUPS


@pytest.fixture
def support_groups():
    call_command("provision_support_roles", stdout=StringIO())
    return Group.objects.in_bulk(SUPPORT_GROUPS, field_name="name")
