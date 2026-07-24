from django.contrib import admin

from .models import (
    CartItem,
    Category,
    Comment,
    Content,
    ContentRating,
    ContentView,
    Course,
    DietPlan,
    DirectMessage,
    Enrollment,
    Follow,
    Lesson,
    Like,
    OutboxEvent,
    Post,
    PostReport,
    Purchase,
    Tag,
    TrainingPlan,
    UserProfile,
    WorkoutRecord,
)

admin.site.site_header = "مدیریت میکروسرویس ۳ PolyLife"
admin.site.register(
    [
        UserProfile,
        DirectMessage,
        Post,
        WorkoutRecord,
        Like,
        Comment,
        Follow,
        PostReport,
        Category,
        Tag,
        Content,
        ContentRating,
        ContentView,
        Course,
        CartItem,
        Purchase,
        Lesson,
        Enrollment,
        TrainingPlan,
        DietPlan,
        OutboxEvent,
    ]
)
