"""
Authentication API endpoints.

Tokens are returned two ways so both browsers and API tools work out of the box:
  * httpOnly cookies (`access_token`, `refresh_token`) for browser frontends.
  * the same tokens in the JSON body for Postman/curl (use as `Bearer`).

These views are CSRF-exempt because they are token-authenticated APIs.
"""

import json

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.auth import api_login_required, resolve_user
from core.jwt_utils import REFRESH, decode_token, make_access_token, make_refresh_token

User = get_user_model()


def _user_dict(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def _set_auth_cookies(resp, access, refresh):
    resp.set_cookie(
        "access_token", access, httponly=True,
        secure=settings.JWT_COOKIE_SECURE, samesite=settings.JWT_COOKIE_SAMESITE,
        path="/", max_age=settings.JWT_ACCESS_TTL_SECONDS,
    )
    resp.set_cookie(
        "refresh_token", refresh, httponly=True,
        secure=settings.JWT_COOKIE_SECURE, samesite=settings.JWT_COOKIE_SAMESITE,
        path="/api/auth/", max_age=settings.JWT_REFRESH_TTL_SECONDS,
    )


def _clear_auth_cookies(resp):
    resp.delete_cookie("access_token", path="/")
    resp.delete_cookie("refresh_token", path="/api/auth/")


def _auth_response(user, status=200):
    access = make_access_token(user)
    refresh = make_refresh_token(user)
    resp = JsonResponse(
        {"user": _user_dict(user), "access": access, "refresh": refresh},
        status=status,
    )
    _set_auth_cookies(resp, access, refresh)
    return resp


@csrf_exempt
@require_POST
def signup(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()

    if not email:
        return JsonResponse({"error": "email is required"}, status=400)
    if not password:
        return JsonResponse({"error": "password is required"}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "invalid email format"}, status=400)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"error": "invalid password", "details": exc.messages}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "email already registered"}, status=409)

    user = User.objects.create_user(
        email=email, password=password, first_name=first_name, last_name=last_name,
    )
    return _auth_response(user, status=201)


@csrf_exempt
@require_POST
def login(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse({"error": "invalid credentials"}, status=401)

    return _auth_response(user)


@csrf_exempt
@require_POST
def refresh(request):
    token = request.COOKIES.get("refresh_token")
    if not token:
        token = (_json_body(request) or {}).get("refresh")
    if not token:
        return JsonResponse({"error": "missing refresh token"}, status=401)

    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "invalid token"}, status=401)

    if payload.get("type") != REFRESH:
        return JsonResponse({"error": "invalid token"}, status=401)

    user = User.objects.filter(id=payload.get("sub"), is_active=True).first()
    if user is None or user.token_version != payload.get("tv"):
        return JsonResponse({"error": "invalid token"}, status=401)

    return _auth_response(user)


@csrf_exempt
@require_POST
def logout(request):
    user = resolve_user(request)
    if user is not None:
        # Invalidate every token issued so far for this user.
        user.token_version += 1
        user.save(update_fields=["token_version"])

    resp = JsonResponse({"ok": True})
    _clear_auth_cookies(resp)
    return resp


@api_login_required
def me(request):
    return JsonResponse({"user": _user_dict(request.user)})
