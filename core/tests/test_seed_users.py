from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class SeedUsersCommandTests(TestCase):
    def test_creates_simple_users(self):
        call_command("seed_users")

        self.assertTrue(User.objects.filter(username="user1").exists())
        self.assertTrue(User.objects.get(username="user1").check_password("user1pass"))

    def test_is_idempotent(self):
        call_command("seed_users")
        call_command("seed_users")  # second run must not error or duplicate

        self.assertEqual(User.objects.filter(username="user1").count(), 1)
