from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from core.jwt_utils import make_access_token, make_refresh_token
from core.middleware import JWTAuthenticationMiddleware

User = get_user_model()


class JWTMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="ali", password="x")
        self.middleware = JWTAuthenticationMiddleware(lambda request: None)

    def _process(self, request):
        # Emulate what Django's AuthenticationMiddleware leaves on the request.
        request.user = AnonymousUser()
        self.middleware.process_request(request)
        return request

    def test_sets_user_from_bearer_header(self):
        token = make_access_token(self.user)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self._process(request)

        self.assertEqual(request.user, self.user)

    def test_sets_user_from_cookie(self):
        request = self.factory.get("/")
        request.COOKIES["access_token"] = make_access_token(self.user)

        self._process(request)

        self.assertEqual(request.user, self.user)

    def test_no_token_leaves_anonymous(self):
        request = self._process(self.factory.get("/"))

        self.assertFalse(request.user.is_authenticated)

    def test_invalid_token_leaves_anonymous(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer not-a-token")

        self._process(request)

        self.assertFalse(request.user.is_authenticated)

    def test_refresh_token_is_not_accepted_as_access(self):
        refresh = make_refresh_token(self.user)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {refresh}")

        self._process(request)

        self.assertFalse(request.user.is_authenticated)

    def test_token_with_stale_version_is_rejected(self):
        token = make_access_token(self.user)
        # Simulate a logout elsewhere bumping the version after the token was issued.
        self.user.token_version += 1
        self.user.save(update_fields=["token_version"])
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self._process(request)

        self.assertFalse(request.user.is_authenticated)
