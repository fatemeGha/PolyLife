"""
Team2 microservice views.

Controllers are intentionally thin:
    - Read request data
    - Call service layer
    - Return standardized response

Business logic lives in services/, NOT here.
"""

from django.views.decorators.http import require_http_methods

from .utils.auth import gateway_auth_required, success_response, error_response


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def health_check(request):
    """
    Public health check endpoint.
    Used by Docker/Nginx to verify the service is running.
    No authentication required.

    GET /api/team2/health/
    """
    return success_response(
        data={"service": "team2", "status": "healthy"},
        message="Service is running",
    )


# ---------------------------------------------------------------------------
# Auth test — requires Gateway headers
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def auth_test(request):
    """
    Protected test endpoint to verify Gateway authentication flow.
    Returns the authenticated user's info extracted from Gateway headers.

    GET /api/team2/auth-test/

    Headers required:
        X-User-Id       : integer
        X-User-Username : string

    Responses:
        200: User info successfully extracted
        401: Missing or invalid Gateway headers
    """
    user_info = request.user_info  # injected by @gateway_auth_required

    return success_response(
        data={
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "message": "Gateway authentication headers received and validated successfully.",
        },
        message="Authenticated successfully",
    )


# ---------------------------------------------------------------------------
# Catch-all for undefined routes
# ---------------------------------------------------------------------------

def not_found(request, exception=None):
    """
    Custom 404 handler for team2 API.
    """
    return error_response(
        message="The requested endpoint does not exist.",
        errors={"path": f"No route matched: {request.path}"},
        status=404,
    )
