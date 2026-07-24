"""Versioned API routes for Team 8."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "team8"

router = DefaultRouter()
router.register("profiles", views.ProfileViewSet, basename="profile")
router.register("messages", views.DirectMessageViewSet, basename="message")
router.register("posts", views.PostViewSet, basename="post")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("tags", views.TagViewSet, basename="tag")
router.register("contents", views.ContentViewSet, basename="content")
router.register("courses", views.CourseViewSet, basename="course")
router.register("cart", views.CartViewSet, basename="cart")
router.register("purchases", views.PurchaseViewSet, basename="purchase")
router.register("lessons", views.LessonViewSet, basename="lesson")
router.register("enrollments", views.EnrollmentViewSet, basename="enrollment")
router.register("training-plans", views.TrainingPlanViewSet, basename="training-plan")
router.register("diet-plans", views.DietPlanViewSet, basename="diet-plan")

urlpatterns = [
    path("api/whoami", views.whoami, name="whoami"),
    path("api/v1/activity/", views.activity_feed, name="activity"),
    path("api/v1/", include(router.urls)),
]
