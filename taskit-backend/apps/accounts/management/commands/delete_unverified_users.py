from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete unverified non-admin users, useful for clearing failed email-verification registrations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete matching users. Without this, only prints what would be deleted.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        queryset = User.objects.filter(
            is_verified=False,
            is_staff=False,
            is_superuser=False,
        ).order_by("date_joined")

        count = queryset.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No unverified non-admin users found."))
            return

        self.stdout.write(f"Found {count} unverified non-admin user(s):")
        for user in queryset:
            self.stdout.write(f"- {user.email}")

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --confirm to delete them."))
            return

        deleted_count, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} unverified non-admin user record(s)."))
