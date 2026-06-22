import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

STRONG_PASSWORD = "Sup3rSecretPass"


class SignupTests(TestCase):
    url = None

    def setUp(self):
        self.url = reverse("core:signup")

    def _post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_signup_creates_user_and_returns_tokens(self):
        resp = self._post({"email": "new@example.com", "password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["user"]["email"], "new@example.com")
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        # httpOnly cookies are set.
        self.assertIn("access_token", resp.cookies)
        self.assertIn("refresh_token", resp.cookies)
        self.assertTrue(resp.cookies["access_token"]["httponly"])

    def test_signup_normalizes_email(self):
        self._post({"email": "Mixed@Example.com", "password": STRONG_PASSWORD})
        self.assertTrue(User.objects.filter(email="mixed@example.com").exists())

    def test_signup_duplicate_email_conflicts(self):
        self._post({"email": "dup@example.com", "password": STRONG_PASSWORD})
        resp = self._post({"email": "dup@example.com", "password": STRONG_PASSWORD})
        self.assertEqual(resp.status_code, 409)

    def test_signup_rejects_invalid_email(self):
        resp = self._post({"email": "not-an-email", "password": STRONG_PASSWORD})
        self.assertEqual(resp.status_code, 400)

    def test_signup_rejects_weak_password(self):
        resp = self._post({"email": "weak@example.com", "password": "123"})
        self.assertEqual(resp.status_code, 400)

    def test_signup_requires_email(self):
        resp = self._post({"password": STRONG_PASSWORD})
        self.assertEqual(resp.status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.url = reverse("core:login")
        User.objects.create_user(email="user@example.com", password=STRONG_PASSWORD)

    def _post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_login_succeeds_with_correct_credentials(self):
        resp = self._post({"email": "user@example.com", "password": STRONG_PASSWORD})

        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())
        self.assertIn("access_token", resp.cookies)

    def test_login_fails_with_wrong_password(self):
        resp = self._post({"email": "user@example.com", "password": "wrong-password"})
        self.assertEqual(resp.status_code, 401)

    def test_login_fails_for_unknown_user(self):
        resp = self._post({"email": "ghost@example.com", "password": STRONG_PASSWORD})
        self.assertEqual(resp.status_code, 401)


class MeEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password=STRONG_PASSWORD)
        login = self.client.post(
            reverse("core:login"),
            data=json.dumps({"email": "user@example.com", "password": STRONG_PASSWORD}),
            content_type="application/json",
        )
        self.access = login.json()["access"]

    def test_me_requires_authentication(self):
        # No cookies / no header.
        self.client.cookies.clear()
        resp = self.client.get(reverse("core:me"))
        self.assertEqual(resp.status_code, 401)

    def test_me_works_with_cookie(self):
        # The test client kept the login cookies.
        resp = self.client.get(reverse("core:me"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user"]["email"], "user@example.com")

    def test_me_works_with_bearer_header(self):
        self.client.cookies.clear()
        resp = self.client.get(
            reverse("core:me"), HTTP_AUTHORIZATION=f"Bearer {self.access}"
        )
        self.assertEqual(resp.status_code, 200)


class RefreshAndLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password=STRONG_PASSWORD)
        self.login_resp = self.client.post(
            reverse("core:login"),
            data=json.dumps({"email": "user@example.com", "password": STRONG_PASSWORD}),
            content_type="application/json",
        )

    def test_refresh_issues_new_access_token(self):
        resp = self.client.post(reverse("core:refresh"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())

    def test_refresh_without_token_is_unauthorized(self):
        self.client.cookies.clear()
        resp = self.client.post(reverse("core:refresh"))
        self.assertEqual(resp.status_code, 401)

    def test_logout_bumps_token_version_and_invalidates_old_tokens(self):
        old_refresh = self.login_resp.json()["refresh"]

        resp = self.client.post(reverse("core:logout"))
        self.assertEqual(resp.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.token_version, 1)

        # The old refresh token (token_version=0) must now be rejected.
        self.client.cookies.clear()
        reuse = self.client.post(
            reverse("core:refresh"),
            data=json.dumps({"refresh": old_refresh}),
            content_type="application/json",
        )
        self.assertEqual(reuse.status_code, 401)
