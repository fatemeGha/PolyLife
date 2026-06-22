from django.urls import path

from . import views

app_name = "__TEAM__"

urlpatterns = [
    path("api/whoami", views.whoami, name="whoami"),
    # Add your team's routes here.
]
