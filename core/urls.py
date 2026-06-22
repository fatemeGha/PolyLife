from django.urls import path

from . import auth_views, views

app_name = "core"

urlpatterns = [
    path("health/", views.health, name="health"),

    # Authentication
    path("auth/signup/", auth_views.signup, name="signup"),
    path("auth/login/", auth_views.login, name="login"),
    path("auth/refresh/", auth_views.refresh, name="refresh"),
    path("auth/logout/", auth_views.logout, name="logout"),
    path("auth/me/", auth_views.me, name="me"),
]
