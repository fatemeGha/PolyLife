import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = "Sup3rSecretPass"


def _login(client):
    return client.post(
        reverse("core:login"),
        data=json.dumps({"username": "ali", "password": PASSWORD}),
        content_type="application/json",
    )


class RefreshTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password=PASSWORD)

    def _refresh(self, token):
        return self.client.post(
            reverse("core:refresh"),
            data=json.dumps({"refresh": token}),
            content_type="application/json",
        )

    def test_login_returns_a_refresh_token(self):
        body = _login(self.client).json()
        self.assertIn("refresh", body)

    def test_refresh_returns_a_working_access_token(self):
        refresh = _login(self.client).json()["refresh"]

        resp = self._refresh(refresh)
        self.assertEqual(resp.status_code, 200)
        new_access = resp.json()["token"]
        self.assertEqual(resp.cookies["access_token"].value, new_access)
        self.assertTrue(resp.cookies["access_token"]["httponly"])

        # The new access token must authenticate /api/user.
        me = self.client.get(
            reverse("core:user"), HTTP_AUTHORIZATION=f"Bearer {new_access}"
        )
        self.assertEqual(me.status_code, 200)

    def test_invalid_refresh_is_rejected(self):
        self.assertEqual(self._refresh("not-a-real-token").status_code, 401)

    def test_access_token_cannot_be_used_as_refresh(self):
        access = _login(self.client).json()["token"]
        self.assertEqual(self._refresh(access).status_code, 401)

    def test_refresh_fails_after_logout(self):
        body = _login(self.client).json()
        refresh, access = body["refresh"], body["token"]

        # Logout bumps token_version, invalidating previously issued tokens.
        self.client.post(reverse("core:logout"), HTTP_AUTHORIZATION=f"Bearer {access}")

        self.assertEqual(self._refresh(refresh).status_code, 401)
