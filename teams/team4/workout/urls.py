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

router = DefaultRouter()

#
# Exercises
#
router.register(
    r"exercises",
    ExerciseViewSet,
    basename="exercises"
)

#
# Workout Programs
#
router.register(
    r"workouts",
    WorkoutProgramViewSet,
    basename="workouts"
)

#
# User Preferences
#
router.register(
    r"preferences",
    UserPreferenceViewSet,
    basename="preferences"
)

#
# Favorites
#
router.register(
    r"favorites",
    FavoriteViewSet,
    basename="favorites"
)

#
# Workout History
#
router.register(
    r"history",
    WorkoutHistoryViewSet,
    basename="history"
)

#
# Reports
#
router.register(
    r"reports",
    ReportViewSet,
    basename="reports"
)


urlpatterns = [

    #
    # Authentication
    #
    path(
        "whoami/",
        whoami,
        name="whoami"
    ),

    #
    # REST APIs
    #
    path(
        "",
        include(router.urls)
    ),

]