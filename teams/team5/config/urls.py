from django.contrib import admin
from django.urls import include, path

from team5 import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login"),
    path("login/api/", views.login_api, name="login_api"),
    path("api/", include("team5.urls")),
    path("exercises/", views.exercise_page, name="exercise_page"),
    path("exercises/<int:pk>/", views.exercise_detail_page, name="exercise_detail"),
    path("workouts/", views.workout_page, name="workouts"),
    path("workouts/<int:pk>/", views.workout_detail_page, name="workout_detail"),
    path("preferences/", views.preference_page, name="preferences"),
    path("favorites/", views.favorite_page, name="favorites"),
    path("history/", views.history_page, name="history"),
    path("reports/", views.report_page, name="reports"),
]