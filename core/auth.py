"""
Request-level authentication helpers.

`resolve_user` turns an incoming request into the authenticated user by reading
the access token from either the `access_token` cookie or an
`Authorization: Bearer <token>` header. The JWT middleware (added later) reuses
the same helper, so the auth logic lives in exactly one place.
"""

from functools import wraps

import jwt
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from core.jwt_utils import ACCESS, decode_token

User = get_user_model()


def extract_access_token(request):
    token = request.COOKIES.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def resolve_user(request):
    """Return the user for the request's access token, or None if unauthenticated."""
    token = extract_access_token(request)
    if not token:
        return None

    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        # Covers expired, malformed, and bad-signature tokens.
        return None

    if payload.get("type") != ACCESS:
        return None

    user = User.objects.filter(id=payload.get("sub"), is_active=True).first()
    if user is None or user.token_version != payload.get("tv"):
        return None

    return user


def api_login_required(view_func):
    """Require a valid access token. Works with or without the JWT middleware."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            user = resolve_user(request)
            if user is None:
                return JsonResponse({"detail": "Authentication required"}, status=401)
            request.user = user
        return view_func(request, *args, **kwargs)

    return _wrapped
