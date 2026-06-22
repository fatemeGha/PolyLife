import jwt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core import jwt_utils

User = get_user_model()


class JwtUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="x")

    def test_access_token_has_expected_claims(self):
        token = jwt_utils.make_access_token(self.user)
        payload = jwt_utils.decode_token(token)

        self.assertEqual(payload["sub"], str(self.user.id))
        self.assertEqual(payload["type"], "access")
        self.assertEqual(payload["tv"], self.user.token_version)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    def test_refresh_token_type(self):
        token = jwt_utils.make_refresh_token(self.user)
        payload = jwt_utils.decode_token(token)

        self.assertEqual(payload["type"], "refresh")

    def test_token_carries_current_token_version(self):
        self.user.token_version = 5
        self.user.save()

        payload = jwt_utils.decode_token(jwt_utils.make_access_token(self.user))

        self.assertEqual(payload["tv"], 5)

    def test_garbage_token_is_invalid(self):
        with self.assertRaises(jwt.InvalidTokenError):
            jwt_utils.decode_token("not-a-real-token")

    @override_settings(JWT_ACCESS_TTL_SECONDS=-10)
    def test_expired_token_raises(self):
        token = jwt_utils.make_access_token(self.user)

        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt_utils.decode_token(token)

    def test_token_signed_with_other_secret_is_invalid(self):
        secret_a = "secret-A-" + "x" * 32
        secret_b = "secret-B-" + "y" * 32

        with override_settings(JWT_SECRET=secret_a):
            token = jwt_utils.make_access_token(self.user)

        # Same token, different verifying secret -> signature check fails.
        with override_settings(JWT_SECRET=secret_b):
            with self.assertRaises(jwt.InvalidTokenError):
                jwt_utils.decode_token(token)
