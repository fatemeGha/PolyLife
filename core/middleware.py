"""JWT authentication middleware."""

from django.utils.deprecation import MiddlewareMixin

from core.auth import resolve_user


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Populate ``request.user`` from a JWT access token (cookie or Bearer header).

    Runs right after Django's ``AuthenticationMiddleware``. If a session already
    authenticated the user (e.g. the admin site), that takes precedence and the
    JWT check is skipped. Otherwise a valid token sets ``request.user``; an
    invalid or missing token leaves it as ``AnonymousUser``.
    """

    def process_request(self, request):
        existing = getattr(request, "user", None)
        if existing is not None and existing.is_authenticated:
            return

        user = resolve_user(request)
        if user is not None:
            request.user = user
