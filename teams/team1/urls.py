from django.urls import path

from . import views

app_name = "team1"

urlpatterns = [
    path("api/whoami", views.whoami, name="whoami"),
    # Add your team's routes here.
]
