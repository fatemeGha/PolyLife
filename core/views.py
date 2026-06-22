from django.conf import settings
from django.http import HttpResponse, JsonResponse

# Shown in the sidebar before any real team microservice exists, so the UI is
# never empty during early development.
DECOY_MICROSERVICES = [
    {"slug": f"team{i}", "name": f"میکروسرویس {i}", "url": "#", "implemented": False}
    for i in range(1, 7)
]


def health(request):
    """Liveness probe used by Docker, CI, and uptime checks."""
    return JsonResponse({"status": "ok", "service": "polylife-core"})


def microservices(request):
    """
    List the team microservices for the sidebar.

    Built from settings.TEAM_APPS once teams exist; until then a decoy list of
    placeholders is returned so the sidebar still renders.
    """
    teams = settings.TEAM_APPS
    if teams:
        items = [
            {"slug": t, "name": t, "url": f"/{t}/", "implemented": True} for t in teams
        ]
    else:
        items = DECOY_MICROSERVICES
    return JsonResponse({"success": True, "microservices": items})


def home(request):
    """
    Serve the built frontend SPA.

    Acts as the catch-all for client-side routes too (e.g. /login, /register):
    if the SPA is built, its index.html is returned and the React router takes
    over. If it is not built (local run without Docker), a minimal placeholder
    is returned instead.
    """
    index_file = settings.FRONTEND_DIST / "index.html"
    if index_file.exists():
        return HttpResponse(index_file.read_bytes())
    return HttpResponse(
        "<h1>PolyLife core</h1>"
        "<p>API is running. Build the frontend with Docker to see the home page.</p>",
        content_type="text/html; charset=utf-8",
    )
