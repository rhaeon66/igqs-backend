import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a staff superuser from environment variables if missing."

    def handle(self, *args, **options):
        username = (
            os.getenv("DJANGO_SUPERUSER_USERNAME")
            or os.getenv("STAFF_USERNAME")
            or ""
        ).strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or os.getenv("STAFF_PASSWORD") or ""
        email = (
            os.getenv("DJANGO_SUPERUSER_EMAIL")
            or os.getenv("DEFAULT_FROM_EMAIL")
            or "admissions@igqs.edu.bd"
        ).strip()
        if "<" in email and ">" in email:
            email = email[email.find("<") + 1 : email.find(">")].strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME/PASSWORD or STAFF_USERNAME/PASSWORD "
                    "not set; skipping createsu."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if not created:
            self.stdout.write(self.style.SUCCESS(f"Superuser {username} already exists."))
            return

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Superuser {username} created."))
