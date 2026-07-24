"""Consistent, Persian-friendly API error envelopes."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and set(detail) == {"detail"}:
        message = str(detail["detail"])
    else:
        message = "اطلاعات ارسال‌شده معتبر نیست."

    response.data = {
        "success": False,
        "code": getattr(exc, "default_code", "api_error"),
        "message": message,
        "errors": detail,
    }
    return response

