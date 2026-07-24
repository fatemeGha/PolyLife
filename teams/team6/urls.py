from django.urls import path

from .views import (
    EquipmentOptionsView,
    FitnessGoalListView,
    GroupRecommendationView,
    HealthView,
    InjuryOptionsView,
    OptionsView,
    ProfileView,
    RiskAnalysisView,
    TrainingGroupDetailView,
    TrainingGroupListView,
)


app_name = "team6"

urlpatterns = [
    path(
        "health",
        HealthView.as_view(),
        name="health",
    ),
    path(
        "goals",
        FitnessGoalListView.as_view(),
        name="goal-list",
    ),
    path(
        "options",
        OptionsView.as_view(),
        name="options",
    ),
    path(
        "equipment",
        EquipmentOptionsView.as_view(),
        name="equipment-options",
    ),
    path(
        "injury-options",
        InjuryOptionsView.as_view(),
        name="injury-options",
    ),
    path(
        "profile",
        ProfileView.as_view(),
        name="profile",
    ),
    path(
        "groups",
        TrainingGroupListView.as_view(),
        name="group-list",
    ),
    path(
        "groups/recommend",
        GroupRecommendationView.as_view(),
        name="group-recommend",
    ),
    path(
        "groups/<int:group_id>",
        TrainingGroupDetailView.as_view(),
        name="group-detail",
    ),
    path(
        "risk-analysis",
        RiskAnalysisView.as_view(),
        name="risk-analysis",
    ),
]