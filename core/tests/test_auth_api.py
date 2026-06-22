import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

STRONG_PASSWORD = "Sup3rSecretPass"


def _post(client, name, payload):
    return client.post(
        reverse(name), data=json.dumps(payload), content_type="application/json"
    )


class RegisterTests(TestCase):
    def test_register_creates_user(self):
        resp = _post(
            self.client,
            "core:register",
            {"username": "ali", "password": STRONG_PASSWORD, "first_name": "Ali"},
        )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["user"]["username"], "ali")
        self.assertEqual(body["user"]["first_name"], "Ali")
        self.assertIn("id", body["user"])
        self.assertTrue(User.objects.filter(username="ali").exists())

    def test_register_duplicate_username_fails(self):
        _post(self.client, "core:register", {"username": "ali", "password": STRONG_PASSWORD})
        resp = _post(self.client, "core:register", {"username": "ali", "password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])

    def test_register_weak_password_fails(self):
        resp = _post(self.client, "core:register", {"username": "ali", "password": "123"})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])

    def test_register_requires_username(self):
        resp = _post(self.client, "core:register", {"password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])


class LoginTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="ali", password=STRONG_PASSWORD)

    def test_login_succeeds_and_returns_token(self):
        resp = _post(self.client, "core:login", {"username": "ali", "password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("token", body)
        self.assertEqual(body["user"]["username"], "ali")

    def test_login_wrong_password_fails(self):
        resp = _post(self.client, "core:login", {"username": "ali", "password": "wrong"})

        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()["success"])

    def test_login_unknown_user_fails(self):
        resp = _post(self.client, "core:login", {"username": "ghost", "password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 401)


class UserEndpointTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="ali", password=STRONG_PASSWORD)
        login = _post(self.client, "core:login", {"username": "ali", "password": STRONG_PASSWORD})
        self.token = login.json()["token"]

    def _auth_get(self, name):
        return self.client.get(reverse(name), HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_user_requires_authentication(self):
        resp = self.client.get(reverse("core:user"))

        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()["success"])

    def test_user_returns_profile_with_bearer_token(self):
        resp = self._auth_get("core:user")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["user"]["username"], "ali")

    def test_logout_invalidates_token(self):
        logout = self.client.post(
            reverse("core:logout"), HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertEqual(logout.status_code, 200)

        # The same token must no longer work after logout.
        resp = self._auth_get("core:user")
        self.assertEqual(resp.status_code, 401)
