from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.jwt_utils import make_access_token

User = get_user_model()


class VerifyEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="Sup3rSecretPass")
        self.token = make_access_token(self.user)

    def test_valid_token_allows_and_returns_identity_headers(self):
        resp = self.client.get(
            reverse("core:verify"), HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-User-Id"], str(self.user.id))
        self.assertEqual(resp["X-User-Username"], "ali")

    def test_missing_token_is_denied(self):
        resp = self.client.get(reverse("core:verify"))

        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_is_denied(self):
        resp = self.client.get(
            reverse("core:verify"), HTTP_AUTHORIZATION="Bearer garbage.token.here"
        )

        self.assertEqual(resp.status_code, 401)
