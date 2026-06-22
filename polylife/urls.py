"""URL configuration for the PolyLife core project."""

from django.contrib import admin
from django.urls import include, path, re_path

from core.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),

    # Catch-all: serve the SPA (and its client-side routes). Must stay last.
    re_path(r"^.*$", home, name="home"),
]
