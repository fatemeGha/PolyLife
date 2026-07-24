from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "team2 backend is up"})


urlpatterns = [
    path("", health),
    path("api/team2/", include("teams.team2.urls")),
]