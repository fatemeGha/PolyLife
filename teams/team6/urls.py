from django.urls import path

from .views import (
    GroupRecommendationView,
    HealthView,
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