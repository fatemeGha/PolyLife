import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_sets_email_and_hashes_password(self):
        user = User.objects.create_user(email="a@example.com", password="secret123")

        self.assertEqual(user.email, "a@example.com")
        # Password must be stored hashed, never in plain text.
        self.assertNotEqual(user.password, "secret123")
        self.assertTrue(user.check_password("secret123"))

    def test_create_user_normalizes_email_domain(self):
        user = User.objects.create_user(email="a@EXAMPLE.COM", password="x")

        self.assertEqual(user.email, "a@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_new_user_defaults(self):
        user = User.objects.create_user(email="a@example.com", password="x")

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.token_version, 0)

    def test_create_superuser_flags(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="x")

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)


class UserModelTests(TestCase):
    def test_id_is_uuid(self):
        user = User.objects.create_user(email="a@example.com", password="x")

        self.assertIsInstance(user.id, uuid.UUID)

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_str_returns_email(self):
        user = User.objects.create_user(email="a@example.com", password="x")

        self.assertEqual(str(user), "a@example.com")

    def test_email_is_unique(self):
        User.objects.create_user(email="a@example.com", password="x")

        with self.assertRaises(Exception):
            User.objects.create_user(email="a@example.com", password="y")
