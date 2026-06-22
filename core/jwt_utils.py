"""
JWT helpers for the PolyLife core.

Two token types are issued:
  * access  — short-lived, sent on every API request.
  * refresh — long-lived, used only to mint new access tokens.

Both carry the user's `token_version` (`tv`). Bumping `User.token_version`
(e.g. on logout) invalidates every token issued before the bump.
"""

from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

ACCESS = "access"
REFRESH = "refresh"


def _encode(payload, ttl_seconds):
    now = datetime.now(timezone.utc)
    body = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(body, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def make_access_token(user):
    return _encode(
        {"sub": str(user.id), "type": ACCESS, "tv": user.token_version},
        settings.JWT_ACCESS_TTL_SECONDS,
    )


def make_refresh_token(user):
    return _encode(
        {"sub": str(user.id), "type": REFRESH, "tv": user.token_version},
        settings.JWT_REFRESH_TTL_SECONDS,
    )


def decode_token(token):
    """
    Decode and verify a token's signature and expiry.

    Raises ``jwt.ExpiredSignatureError`` if expired, or
    ``jwt.InvalidTokenError`` (its base class) for any other problem.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
