from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

# A few simple demo users for the core database (dev only).
SIMPLE_USERS = [
    ("user1", "user1pass"),
    ("user2", "user2pass"),
    ("user3", "user3pass"),
]


class Command(BaseCommand):
    help = "Create a few simple demo users in the core database (idempotent)."

    def handle(self, *args, **options):
        created = 0
        for username, password in SIMPLE_USERS:
            user, made = User.objects.get_or_create(username=username)
            if made:
                user.set_password(password)
                user.save()
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_users: {created} created, "
                f"{len(SIMPLE_USERS) - created} already existed"
            )
        )
