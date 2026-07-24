from django.utils import timezone
from django.conf import settings
from rest_framework.test import APITestCase

from ..models import (
    Category,
    Content,
    ContentStatus,
    ContentType,
    Course,
    CourseStatus,
    Lesson,
    Post,
    PostStatus,
    UserProfile,
    UserRole,
)


class Team8APITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.athlete = UserProfile.objects.create(
            user_id=1,
            username="amir",
            display_name="Amirhossein Bagheri",
            role=UserRole.ATHLETE,
        )
        self.coach = UserProfile.objects.create(
            user_id=2,
            username="coach",
            display_name="Coach Sara",
            role=UserRole.COACH,
            is_verified=True,
        )
        self.specialist = UserProfile.objects.create(
            user_id=3,
            username="nutrition",
            display_name="Dr Nutrition",
            role=UserRole.NUTRITION_SPECIALIST,
            is_verified=True,
        )
        self.stranger = UserProfile.objects.create(
            user_id=4,
            username="stranger",
            display_name="Stranger",
        )
        self.category = Category.objects.create(
            name="Fitness",
            slug="fitness",
            description="Fitness education",
        )
        self.authenticate()

    def authenticate(self, user_id=1, username="amir"):
        self.client.credentials(
            HTTP_X_USER_ID=str(user_id),
            HTTP_X_USER_USERNAME=username,
            HTTP_X_GATEWAY_SECRET=settings.GATEWAY_SHARED_SECRET,
        )

    def create_post(self, author_id=2, username="coach", body="تمرین امروز"):
        return Post.objects.create(
            author_id=author_id,
            author_username=username,
            body=body,
            status=PostStatus.PUBLISHED,
            published_at=timezone.now(),
        )

    def create_content(self, author_id=2, status=ContentStatus.PUBLISHED):
        return Content.objects.create(
            author_id=author_id,
            author_username="coach",
            title=f"Warm up {Content.all_objects.count()}",
            slug=f"warm-up-{Content.all_objects.count()}",
            content_type=ContentType.ARTICLE,
            category=self.category,
            body="Educational body",
            status=status,
            published_at=timezone.now() if status == ContentStatus.PUBLISHED else None,
        )

    def create_course(self, author_id=2, status=CourseStatus.PUBLISHED, is_free=True):
        course = Course.objects.create(
            author_id=author_id,
            author_username="coach",
            title=f"Starter Course {Course.all_objects.count()}",
            slug=f"starter-course-{Course.all_objects.count()}",
            description="Course description",
            category=self.category,
            is_free=is_free,
            price=0 if is_free else 120000,
            status=status,
            published_at=timezone.now() if status == CourseStatus.PUBLISHED else None,
        )
        Lesson.objects.create(
            course=course,
            title="Lesson one",
            order=1,
            body="Lesson body",
            duration_minutes=10,
        )
        return course

    @staticmethod
    def items(response):
        return response.data.get("results", response.data)
