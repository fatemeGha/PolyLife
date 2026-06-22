"""
Authentication API endpoints.

Contract (consumed by the home-page frontend):
  POST /api/register  {username, password}  -> 201 {success, message, user}
  POST /api/login     {username, password}  -> 200 {success, message, token, user}
  GET  /api/user      (Bearer token)        -> 200 {success, user}
  POST /api/logout    (Bearer token)        -> 200 {success, message}
  GET  /api/verify    (Bearer / cookie)     -> 200 + X-User-* headers (forward-auth)

All errors share the shape {success: false, message: "..."}.
These views are CSRF-exempt because they are token-authenticated APIs.
"""

import json
from urllib.parse import quote

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.auth import api_login_required
from core.jwt_utils import make_access_token

User = get_user_model()


def _user_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def _error(message, status):
    return JsonResponse({"success": False, "message": message}, status=status)


@csrf_exempt
@require_POST
def register(request):
    data = _json_body(request)
    if data is None:
        return _error("بدنه‌ی درخواست نامعتبر است", 400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()

    if not username:
        return _error("نام کاربری الزامی است", 400)
    if not password:
        return _error("رمز عبور الزامی است", 400)

    if User.objects.filter(username=username).exists():
        return _error("نام کاربری تکراری است", 400)

    try:
        validate_password(password)
    except ValidationError:
        return _error("رمز عبور ضعیف است", 400)

    user = User.objects.create_user(
        username=username, password=password, first_name=first_name, last_name=last_name
    )
    return JsonResponse(
        {"success": True, "message": "ثبت‌نام با موفقیت انجام شد", "user": _user_dict(user)},
        status=201,
    )


@csrf_exempt
@require_POST
def login(request):
    data = _json_body(request)
    if data is None:
        return _error("بدنه‌ی درخواست نامعتبر است", 400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = authenticate(request, username=username, password=password)
    if user is None:
        return _error("نام کاربری یا رمز عبور اشتباه است", 401)

    return JsonResponse(
        {
            "success": True,
            "message": "ورود با موفقیت انجام شد",
            "token": make_access_token(user),
            "user": _user_dict(user),
        }
    )


@require_GET
@api_login_required
def user(request):
    return JsonResponse({"success": True, "user": _user_dict(request.user)})


@csrf_exempt
@require_POST
@api_login_required
def logout(request):
    # Invalidate every token issued so far for this user.
    request.user.token_version += 1
    request.user.save(update_fields=["token_version"])
    return JsonResponse({"success": True, "message": "خروج با موفقیت انجام شد"})


@require_GET
@api_login_required
def verify(request):
    """
    Forward-auth endpoint for team gateways.

    A team's nginx gateway calls this (via `auth_request`) for every protected
    request. A 200 means "allowed"; the identity is returned in headers the
    gateway forwards to the team backend. A 401 means "denied".

    The username is URL-encoded so the header stays ASCII-safe.
    """
    resp = JsonResponse({"success": True})
    resp["X-User-Id"] = str(request.user.id)
    resp["X-User-Username"] = quote(request.user.username)
    return resp
