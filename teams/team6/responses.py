from typing import Any

from django.http import JsonResponse


def success_response(
    message: str,
    data: Any = None,
    status: int = 200,
) -> JsonResponse:
    """
    Return a standardized successful API response.
    """
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }

    return JsonResponse(payload, status=status)


def error_response(
    code: str,
    message: str,
    details: Any = None,
    status: int = 400,
) -> JsonResponse:
    """
    Return a standardized error API response.
    """
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details if details is not None else {},
        },
    }

    return JsonResponse(payload, status=status)