from rest_framework import status
from rest_framework.response import Response


def success_response(
    *,
    data=None,
    message="Operation completed successfully",
    status_code=status.HTTP_200_OK,
):
    if data is None:
        data = {}

    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def error_response(
    *,
    code,
    message,
    details=None,
    status_code=status.HTTP_400_BAD_REQUEST,
):
    if details is None:
        details = {}

    return Response(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
        status=status_code,
    )


def validation_error_response(errors):
    return error_response(
        code="VALIDATION_ERROR",
        message="Some required fields are missing or invalid.",
        details=errors,
        status_code=status.HTTP_400_BAD_REQUEST,
    )