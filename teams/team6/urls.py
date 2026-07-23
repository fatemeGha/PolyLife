from django.urls import path

from .views import HealthView, ProfileView


app_name = "team6"

urlpatterns = [
    path(
        "health",
        HealthView.as_view(),
        name="health",
    ),
    path(
        "profile",
        ProfileView.as_view(),
        name="profile",
    ),
]