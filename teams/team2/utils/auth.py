"""
Authentication utilities for Team2 microservice.

In this architecture, JWT decoding is handled by the Gateway (Nginx).
The backend trusts the headers forwarded by the Gateway and does NOT
decode JWT tokens directly.

Headers injected by Gateway:
    X-User-Id       : Authenticated user's primary key (integer)
    X-User-Username : Authenticated user's username (string)
"""

import functools
from django.http import JsonResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADER_USER_ID = "HTTP_X_USER_ID"          # Django converts X-User-Id → HTTP_X_USER_ID
HEADER_USER_USERNAME = "HTTP_X_USER_USERNAME"  # Django converts X-User-Username → HTTP_X_USER_USERNAME


# ---------------------------------------------------------------------------
# Helper: extract user info from request headers
# ---------------------------------------------------------------------------

def get_user_from_request(request):
    """
    Extract authenticated user information from Gateway-injected headers.

    Returns a dict with user info on success, or None if headers are missing/invalid.

    Args:
        request: Django HttpRequest object

    Returns:
        dict: {"user_id": int, "username": str} on success
        None: if headers are missing or user_id is not a valid integer
    """
    raw_user_id = request.META.get(HEADER_USER_ID)
    username = request.META.get(HEADER_USER_USERNAME)

    # Both headers must be present
    if not raw_user_id or not username:
        return None

    # user_id must be a valid positive integer
    try:
        user_id = int(raw_user_id)
        if user_id <= 0:
            raise ValueError("user_id must be a positive integer")
    except (ValueError, TypeError):
        return None

    return {
        "user_id": user_id,
        "username": username.strip(),
    }


# ---------------------------------------------------------------------------
# Standard JSON response builders
# ---------------------------------------------------------------------------

def success_response(data=None, message="Operation completed successfully", status=200):
    """
    Build a standardized success JSON response.

    Args:
        data    : Payload to include in the response body
        message : Human-readable success message
        status  : HTTP status code (default: 200)

    Returns:
        JsonResponse
    """
    body = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }
    return JsonResponse(body, status=status)


def error_response(message="An error occurred", errors=None, status=400):
    """
    Build a standardized error JSON response.

    Args:
        message : Human-readable error description
        errors  : Dict or list with field-level error details (optional)
        status  : HTTP status code (default: 400)

    Returns:
        JsonResponse
    """
    body = {
        "success": False,
        "message": message,
        "errors": errors if errors is not None else {},
    }
    return JsonResponse(body, status=status)


# ---------------------------------------------------------------------------
# Decorator: gateway_auth_required
# ---------------------------------------------------------------------------

def gateway_auth_required(view_func):
    """
    Decorator that enforces Gateway-based authentication for Django views.

    Behavior:
        - Reads X-User-Id and X-User-Username from request headers.
        - Injects a `request.user_info` dict into the request object for use
          inside the decorated view.
        - Returns HTTP 401 if headers are missing or malformed.
        - Does NOT decode JWT tokens — that is the Gateway's responsibility.

    Usage:
        @gateway_auth_required
        def my_view(request):
            user_id = request.user_info["user_id"]
            username = request.user_info["username"]
            ...

    Args:
        view_func: The Django view function to wrap.

    Returns:
        Wrapped view function with authentication enforcement.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_info = get_user_from_request(request)

        if user_info is None:
            return error_response(
                message="Authentication required. Gateway headers X-User-Id and X-User-Username are missing or invalid.",
                errors={
                    "X-User-Id": "Must be present and a valid positive integer.",
                    "X-User-Username": "Must be present and non-empty.",
                },
                status=401,
            )

        # Attach user info to the request object so the view can access it
        request.user_info = user_info

        return view_func(request, *args, **kwargs)

    return wrapper
