from django.urls import path

from . import views

app_name = "team5"

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    whoami,
    ExerciseViewSet,
    WorkoutProgramViewSet,
    UserPreferenceViewSet,
    FavoriteViewSet,
    WorkoutHistoryViewSet,
    ReportViewSet,
)

app_name = "team5"

router = DefaultRouter()

router.register(r"exercises", ExerciseViewSet, basename="exercises")
router.register(r"workouts", WorkoutProgramViewSet, basename="workouts")
router.register(r"preferences", UserPreferenceViewSet, basename="preferences")
router.register(r"favorites", FavoriteViewSet, basename="favorites")
router.register(r"history", WorkoutHistoryViewSet, basename="history")
router.register(r"reports", ReportViewSet, basename="reports")

urlpatterns = [
    path("whoami/", whoami, name="whoami"),
    path("", include(router.urls)),
]
