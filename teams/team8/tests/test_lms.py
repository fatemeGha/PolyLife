import json

from rest_framework import status

from ..models import (
    Category,
    Content,
    ContentRating,
    ContentStatus,
    Course,
    DietPlan,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    Tag,
    TrainingPlan,
)
from .common import Team8APITestCase


class ContentApiTests(Team8APITestCase):
    def test_athlete_cannot_create_content_or_category(self):
        response = self.client.post(
            "/api/v1/contents/",
            {
                "title": "Unauthorized",
                "content_type": "article",
                "category": str(self.category.id),
                "body": "Body",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(
            "/api/v1/categories/",
            {"name": "New category"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unverified_expert_cannot_create_content(self):
        self.stranger.role = "coach"
        self.stranger.save(update_fields=["role", "updated_at"])
        self.authenticate(4, "stranger")
        response = self.client.post(
            "/api/v1/contents/",
            {
                "title": "Unverified",
                "content_type": "article",
                "category": str(self.category.id),
                "body": "Body",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_create_multipart_content_with_json_tags(self):
        self.authenticate(2, "coach")
        response = self.client.post(
            "/api/v1/contents/",
            {
                "title": "Safe warm up",
                "content_type": "article",
                "category": str(self.category.id),
                "body": "Detailed guide",
                "status": "published",
                "difficulty": "beginner",
                "duration_minutes": 8,
                "tag_names": json.dumps(["warmup", "mobility", "warmup"]),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data["tags"]), {"warmup", "mobility"})
        self.assertEqual(Tag.objects.count(), 2)

    def test_published_video_requires_media(self):
        self.authenticate(2, "coach")
        response = self.client.post(
            "/api/v1/contents/",
            {
                "title": "Video",
                "content_type": "video",
                "category": str(self.category.id),
                "body": "Video body",
                "status": "published",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_content_search_category_filter_and_malformed_category(self):
        content = self.create_content()
        response = self.client.get("/api/v1/contents/?q=Warm&category=fitness")
        self.assertEqual(self.items(response)[0]["id"], str(content.id))
        response = self.client.get("/api/v1/contents/?category=not-a-uuid")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.items(response), [])

    def test_draft_visibility_publish_archive_and_owner_protection(self):
        draft = self.create_content(status=ContentStatus.DRAFT)
        response = self.client.get(f"/api/v1/contents/{draft.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.authenticate(2, "coach")
        response = self.client.post(f"/api/v1/contents/{draft.id}/publish/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ContentStatus.PUBLISHED)
        response = self.client.post(f"/api/v1/contents/{draft.id}/archive/")
        self.assertEqual(response.data["status"], ContentStatus.ARCHIVED)
        self.authenticate(3, "nutrition")
        response = self.client.patch(
            f"/api/v1/contents/{draft.id}/",
            {"title": "Stolen"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_content_delete_detaches_lesson_and_category_delete_is_protected(self):
        content = self.create_content()
        course = self.create_course()
        lesson = course.lessons.first()
        lesson.content = content
        lesson.save(update_fields=["content", "updated_at"])
        self.authenticate(2, "coach")
        response = self.client.delete(f"/api/v1/contents/{content.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        lesson.refresh_from_db()
        self.assertIsNone(lesson.content_id)
        response = self.client.delete(f"/api/v1/categories/{self.category.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_is_upserted_and_recommendations_match_category(self):
        first = self.create_content()
        second = self.create_content()
        other_category = Category.objects.create(name="Yoga", slug="yoga")
        unrelated = self.create_content()
        unrelated.category = other_category
        unrelated.save()
        response = self.client.put(
            f"/api/v1/contents/{first.id}/rate/",
            {"score": 4},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.put(
            f"/api/v1/contents/{first.id}/rate/",
            {"score": 5},
            format="json",
        )
        self.assertEqual(ContentRating.objects.get(content=first, user_id=1).score, 5)
        response = self.client.get(f"/api/v1/contents/{first.id}/recommendations/")
        ids = {item["id"] for item in response.data}
        self.assertIn(str(second.id), ids)
        self.assertNotIn(str(unrelated.id), ids)

    def test_recommendations_use_recent_view_history(self):
        viewed = self.create_content()
        same_category = self.create_content()
        other_category = Category.objects.create(name="Yoga", slug="yoga")
        other_viewed = self.create_content()
        other_viewed.category = other_category
        other_viewed.save(update_fields=["category", "updated_at"])
        other_recommendation = self.create_content()
        other_recommendation.category = other_category
        other_recommendation.save(update_fields=["category", "updated_at"])

        self.client.get(f"/api/v1/contents/{viewed.id}/")
        self.client.get(f"/api/v1/contents/{other_viewed.id}/")
        response = self.client.get(f"/api/v1/contents/{viewed.id}/recommendations/")
        ids = {item["id"] for item in response.data}

        self.assertIn(str(same_category.id), ids)
        self.assertIn(str(other_recommendation.id), ids)
        self.assertNotIn(str(viewed.id), ids)
        self.assertNotIn(str(other_viewed.id), ids)


class CourseApiTests(Team8APITestCase):
    def test_creator_can_create_nested_course_from_multipart_json(self):
        self.authenticate(2, "coach")
        response = self.client.post(
            "/api/v1/courses/",
            {
                "title": "Strength basics",
                "description": "Complete course",
                "category": str(self.category.id),
                "status": "published",
                "is_free": "true",
                "tag_names": json.dumps(["strength"]),
                "lessons": json.dumps(
                    [
                        {
                            "title": "Start",
                            "order": 1,
                            "body": "First lesson",
                            "duration_minutes": 12,
                            "is_preview": True,
                        },
                        {
                            "title": "Continue",
                            "order": 2,
                            "body": "Second lesson",
                            "duration_minutes": 18,
                            "is_preview": False,
                        },
                    ]
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["lesson_count"], 2)
        self.assertEqual(response.data["duration_minutes"], 30)

    def test_published_course_needs_lesson_and_paid_course_needs_price(self):
        self.authenticate(2, "coach")
        base = {
            "title": "Invalid course",
            "description": "Description",
            "category": str(self.category.id),
            "status": "published",
        }
        response = self.client.post("/api/v1/courses/", base, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        base["lessons"] = [{"title": "One", "order": 1}]
        base["is_free"] = False
        response = self.client.post("/api/v1/courses/", base, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        base["price"] = 450000
        response = self.client.post("/api/v1/courses/", base, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["price"], 450000)

    def test_duplicate_lesson_order_is_rejected(self):
        self.authenticate(2, "coach")
        response = self.client.post(
            "/api/v1/courses/",
            {
                "title": "Duplicate order",
                "description": "Invalid",
                "category": str(self.category.id),
                "lessons": [
                    {"title": "First", "order": 1},
                    {"title": "Second", "order": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        course = self.create_course()
        response = self.client.patch(
            f"/api/v1/courses/{course.id}/",
            {"lessons": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_removed_lesson_order_can_be_reactivated(self):
        course = self.create_course()
        second = Lesson.objects.create(course=course, title="Second", order=2)
        self.authenticate(2, "coach")
        response = self.client.patch(
            f"/api/v1/courses/{course.id}/",
            {
                "lessons": [
                    {"title": "Lesson one", "order": 1, "duration_minutes": 10}
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Lesson.objects.filter(pk=second.id).exists())
        response = self.client.patch(
            f"/api/v1/courses/{course.id}/",
            {
                "lessons": [
                    {"title": "Lesson one", "order": 1, "duration_minutes": 10},
                    {"title": "Second restored", "order": 2, "duration_minutes": 5},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lesson_count"], 2)
        self.assertEqual(Lesson.objects.get(pk=second.id).title, "Second restored")

    def test_enroll_is_idempotent_and_initializes_progress(self):
        course = self.create_course()
        first = self.client.post(f"/api/v1/courses/{course.id}/enroll/", {}, format="json")
        second = self.client.post(f"/api/v1/courses/{course.id}/enroll/", {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Enrollment.objects.filter(user_id=1, course=course).count(), 1)
        self.assertEqual(LessonProgress.objects.filter(enrollment_id=first.data["id"]).count(), 1)

    def test_draft_or_paid_course_cannot_be_enrolled(self):
        draft = self.create_course(status="draft")
        response = self.client.post(f"/api/v1/courses/{draft.id}/enroll/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        paid = self.create_course(is_free=False)
        response = self.client.post(f"/api/v1/courses/{paid.id}/enroll/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lesson_progress_completes_course(self):
        course = self.create_course()
        enrollment_response = self.client.post(
            f"/api/v1/courses/{course.id}/enroll/",
            {},
            format="json",
        )
        enrollment_id = enrollment_response.data["id"]
        lesson = course.lessons.first()
        response = self.client.patch(
            f"/api/v1/enrollments/{enrollment_id}/lessons/{lesson.id}/",
            {"watched_seconds": 600, "is_completed": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["progress_percent"], 100)
        self.assertEqual(response.data["status"], EnrollmentStatus.COMPLETED)

    def test_progress_rejects_lesson_from_other_course(self):
        course = self.create_course()
        other = self.create_course()
        enrollment = self.client.post(
            f"/api/v1/courses/{course.id}/enroll/",
            {},
            format="json",
        ).data
        response = self.client.patch(
            f"/api/v1/enrollments/{enrollment['id']}/lessons/{other.lessons.first().id}/",
            {"is_completed": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancelled_enrollment_can_be_reactivated(self):
        course = self.create_course()
        created = self.client.post(
            f"/api/v1/courses/{course.id}/enroll/",
            {},
            format="json",
        )
        self.client.post(f"/api/v1/enrollments/{created.data['id']}/cancel/")
        reactivated = self.client.post(
            f"/api/v1/courses/{course.id}/enroll/",
            {},
            format="json",
        )
        self.assertEqual(reactivated.status_code, status.HTTP_201_CREATED)
        self.assertEqual(reactivated.data["status"], EnrollmentStatus.ACTIVE)

    def test_course_with_enrollment_cannot_be_deleted(self):
        course = self.create_course()
        self.client.post(f"/api/v1/courses/{course.id}/enroll/", {}, format="json")
        self.authenticate(2, "coach")
        response = self.client.delete(f"/api/v1/courses/{course.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Course.objects.filter(pk=course.id).exists())


class PlansApiTests(Team8APITestCase):
    def test_coach_can_create_training_plan_but_athlete_cannot(self):
        payload = {
            "title": "Four weeks",
            "description": "Beginner plan",
            "weeks": 4,
            "exercises": [{"day": 1, "exercise": "Squat"}],
            "is_published": True,
        }
        response = self.client.post("/api/v1/training-plans/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(2, "coach")
        response = self.client.post("/api/v1/training-plans/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TrainingPlan.objects.filter(author_id=2).exists())

    def test_only_nutrition_specialist_or_admin_creates_diet_plan(self):
        payload = {
            "title": "Seven days",
            "description": "Balanced",
            "days": 7,
            "meals": [{"day": 1, "meal": "Breakfast"}],
            "is_published": True,
        }
        self.authenticate(2, "coach")
        response = self.client.post("/api/v1/diet-plans/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(3, "nutrition")
        response = self.client.post("/api/v1/diet-plans/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DietPlan.objects.filter(author_id=3).exists())

    def test_plan_json_fields_must_be_arrays(self):
        self.authenticate(2, "coach")
        response = self.client.post(
            "/api/v1/training-plans/",
            {
                "title": "Invalid",
                "weeks": 2,
                "exercises": {"not": "a list"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
