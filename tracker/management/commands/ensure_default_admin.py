import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a default admin user for bootstrapping environments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("DJANGO_DEFAULT_ADMIN_USERNAME", "admin"),
            help="Admin username.",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("DJANGO_DEFAULT_ADMIN_EMAIL", ""),
            help="Admin email address.",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("DJANGO_DEFAULT_ADMIN_PASSWORD"),
            help="Admin password.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError(
                "Provide --password or set DJANGO_DEFAULT_ADMIN_PASSWORD."
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
            },
        )

        if options["email"]:
            user.email = options["email"]
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} admin user '{user.username}'.")
        )