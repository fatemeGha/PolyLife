from django.urls import path, include
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "team2 backend is up"})


urlpatterns = [
    path("", health),
    path("api/", include("teams.team2.urls")),
]