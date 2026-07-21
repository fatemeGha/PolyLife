from django.urls import path, include
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "team7 backend is up"})


urlpatterns = [
    path("", health),
    path("api/", include("teams.team7.urls")),
]