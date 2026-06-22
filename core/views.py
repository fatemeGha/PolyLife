from django.http import JsonResponse


def health(request):
    """Liveness probe used by Docker, CI, and uptime checks."""
    return JsonResponse({"status": "ok", "service": "polylife-core"})
