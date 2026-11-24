from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.roles import SUPPORT_GROUPS, SUPPORT_PERMISSIONS


class Command(BaseCommand):
    help = "Create or synchronize the two support groups and their model permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        codenames = [permission.split(".")[1] for permission in SUPPORT_PERMISSIONS]
        permissions = list(
            Permission.objects.filter(
                content_type__app_label="support", codename__in=codenames
            )
        )
        if {permission.codename for permission in permissions} != set(codenames) or len(
            permissions
        ) != len(codenames):
            raise CommandError(
                "Expected support model permissions. Run Django migrate first."
            )

        for name in SUPPORT_GROUPS:
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS("Support roles provisioned."))
