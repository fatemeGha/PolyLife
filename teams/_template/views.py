from django.http import JsonResponse


def whoami(request):
    """
    Example endpoint.

    The gateway already authenticated the user against the core and injected
    these headers — your team never decodes JWTs. Just read them.
    """
    return JsonResponse(
        {
            "team": "__TEAM__",
            "user_id": request.headers.get("X-User-Id", ""),
            "username": request.headers.get("X-User-Username", ""),
        }
    )

# Add your team's real views below.
