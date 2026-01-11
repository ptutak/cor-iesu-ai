"""
Management command to fix maintainer permissions.

This command ensures all maintainer users are properly added to the Maintainers
group and have the correct permissions.
"""

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from adoration.models import Maintainer


class Command(BaseCommand):
    """Fix maintainer permissions command."""

    help = "Ensure all maintainer users are in the Maintainers group with correct permissions"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments.

        Args:
            parser: Command argument parser
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Handle the command execution.

        Args:
            args: Positional arguments
            options: Command options
        """
        dry_run = options["dry_run"]

        try:
            maintainer_group = Group.objects.get(name="Maintainers")
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Maintainers group does not exist. Run migrations first."))
            return

        maintainers = Maintainer.objects.select_related("user").all()

        if not maintainers.exists():
            self.stdout.write("No maintainers found.")
            return

        updated_count = 0
        already_correct_count = 0

        with transaction.atomic():
            for maintainer in maintainers:
                user = maintainer.user

                if user.groups.filter(name="Maintainers").exists():
                    already_correct_count += 1
                    self.stdout.write(f"✓ {user.username} already in Maintainers group")
                else:
                    if not dry_run:
                        user.groups.add(maintainer_group)

                    updated_count += 1
                    action = "Would add" if dry_run else "Added"
                    self.stdout.write(self.style.SUCCESS(f"+ {action} {user.username} to Maintainers group"))

        # Summary
        total_maintainers = maintainers.count()
        self.stdout.write(self.style.SUCCESS("\nSummary:"))
        self.stdout.write(f"Total maintainers: {total_maintainers}")
        self.stdout.write(f"Already correct: {already_correct_count}")

        if dry_run:
            self.stdout.write(f"Would update: {updated_count}")
            self.stdout.write(self.style.WARNING("This was a dry run. Use --no-dry-run to apply changes."))
        else:
            self.stdout.write(f"Updated: {updated_count}")

        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS("All maintainers now have correct permissions!"))
