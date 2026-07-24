"""URL configuration for the PolyLife project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from core.views import home


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]

if "teams.team6" in settings.TEAM_APPS:
    urlpatterns.append(
        path("api/", include("teams.team6.urls"))
    )

# این مسیر باید همیشه آخر باشد.
urlpatterns.append(
    re_path(r"^.*$", home, name="home")
)