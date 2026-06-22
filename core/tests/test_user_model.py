from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_sets_fields_and_hashes_password(self):
        user = User.objects.create_user(
            username="ali", password="secret123", first_name="Ali", last_name="Rezaei"
        )

        self.assertEqual(user.username, "ali")
        self.assertEqual(user.first_name, "Ali")
        self.assertEqual(user.last_name, "Rezaei")
        # Password must be stored hashed, never in plain text.
        self.assertNotEqual(user.password, "secret123")
        self.assertTrue(user.check_password("secret123"))

    def test_create_user_without_username_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(username="", password="x")

    def test_new_user_defaults(self):
        user = User.objects.create_user(username="ali", password="x")

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.token_version, 0)

    def test_create_superuser_flags(self):
        admin = User.objects.create_superuser(username="admin", password="x")

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)


class UserModelTests(TestCase):
    def test_id_is_numeric(self):
        user = User.objects.create_user(username="ali", password="x")

        self.assertIsInstance(user.id, int)

    def test_username_field_is_username(self):
        self.assertEqual(User.USERNAME_FIELD, "username")

    def test_str_returns_username(self):
        user = User.objects.create_user(username="ali", password="x")

        self.assertEqual(str(user), "ali")

    def test_username_is_unique(self):
        User.objects.create_user(username="ali", password="x")

        with self.assertRaises(Exception):
            User.objects.create_user(username="ali", password="y")
