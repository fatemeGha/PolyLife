from django.urls import path

from . import auth_views, views

app_name = "core"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("microservices/", views.microservices, name="microservices"),

    # Authentication. Paths match the frontend contract exactly (no trailing
    # slash) so POST requests are not affected by APPEND_SLASH redirects.
    path("register", auth_views.register, name="register"),
    path("login", auth_views.login, name="login"),
    path("user", auth_views.user, name="user"),
    path("logout", auth_views.logout, name="logout"),
    path("verify", auth_views.verify, name="verify"),
]
