"""Authentication adapter for identity headers injected by the Nginx gateway."""

import secrets
from dataclasses import dataclass
from urllib.parse import unquote

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


@dataclass(frozen=True)
class GatewayPrincipal:
    id: int
    username: str

    @property
    def pk(self):
        return self.id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class GatewayHeaderAuthentication(BaseAuthentication):
    """Trust only the identity established by Core and forwarded by Nginx."""

    def authenticate(self, request):
        raw_user_id = request.headers.get("X-User-Id")
        username = request.headers.get("X-User-Username")
        if not raw_user_id or not username:
            return None
        gateway_secret = request.headers.get("X-Gateway-Secret", "")
        if not secrets.compare_digest(gateway_secret, settings.GATEWAY_SHARED_SECRET):
            raise AuthenticationFailed("درخواست از Gateway مورد اعتماد ارسال نشده است.")

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError) as exc:
            raise AuthenticationFailed("شناسه کاربر ارسال‌شده از Gateway معتبر نیست.") from exc

        if user_id <= 0:
            raise AuthenticationFailed("شناسه کاربر باید یک عدد مثبت باشد.")
        try:
            username = unquote(username, errors="strict")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed(
                "نام کاربری ارسال‌شده از Gateway معتبر نیست."
            ) from exc
        if (
            not username
            or len(username) > 150
            or any(ord(character) < 32 or ord(character) == 127 for character in username)
        ):
            raise AuthenticationFailed("نام کاربری ارسال‌شده از Gateway معتبر نیست.")

        return GatewayPrincipal(id=user_id, username=username), None

    def authenticate_header(self, request):
        return "Gateway"
