from rest_framework import status

from ..models import (
    DirectMessage,
    Enrollment,
    Follow,
    Purchase,
)
from .common import Team8APITestCase


class PaidCourseAndLessonAccessTests(Team8APITestCase):
    def test_lesson_body_is_locked_until_enrollment(self):
        course = self.create_course()
        lesson = course.lessons.first()

        locked = self.client.get(f"/api/v1/courses/{course.id}/")
        self.assertEqual(locked.status_code, status.HTTP_200_OK)
        self.assertFalse(locked.data["lessons"][0]["accessible"])
        self.assertEqual(locked.data["lessons"][0]["body"], "")

        self.client.post(f"/api/v1/courses/{course.id}/enroll/", {}, format="json")
        unlocked = self.client.get(f"/api/v1/courses/{course.id}/")
        self.assertTrue(unlocked.data["lessons"][0]["accessible"])
        self.assertEqual(unlocked.data["lessons"][0]["body"], lesson.body)

    def test_preview_lesson_is_open_without_enrollment(self):
        course = self.create_course(is_free=False)
        lesson = course.lessons.first()
        lesson.is_preview = True
        lesson.save(update_fields=["is_preview", "updated_at"])

        response = self.client.get(f"/api/v1/courses/{course.id}/")
        self.assertTrue(response.data["lessons"][0]["accessible"])
        self.assertEqual(response.data["lessons"][0]["body"], lesson.body)

    def test_cart_checkout_immediately_confirms_purchase_and_enrolls(self):
        course = self.create_course(is_free=False)

        added = self.client.post(
            "/api/v1/cart/",
            {"course_id": str(course.id)},
            format="json",
        )
        self.assertEqual(added.status_code, status.HTTP_201_CREATED)
        self.assertEqual(added.data["course"]["price"], course.price)

        checkout = self.client.post("/api/v1/cart/checkout/", {}, format="json")
        self.assertEqual(checkout.status_code, status.HTTP_200_OK)
        self.assertTrue(checkout.data["success"])
        self.assertEqual(checkout.data["purchases"][0]["amount"], course.price)
        self.assertTrue(Purchase.objects.filter(user_id=1, course=course).exists())
        self.assertTrue(Enrollment.objects.filter(user_id=1, course=course).exists())
        self.assertEqual(self.client.get("/api/v1/cart/").data, [])

        history = self.client.get("/api/v1/purchases/")
        self.assertEqual(self.items(history)[0]["course"]["id"], str(course.id))
        detail = self.client.get(f"/api/v1/courses/{course.id}/")
        self.assertTrue(detail.data["purchased"])
        self.assertTrue(detail.data["enrolled"])
        self.assertTrue(detail.data["lessons"][0]["accessible"])

    def test_free_or_already_purchased_course_cannot_enter_cart(self):
        free = self.create_course()
        response = self.client.post(
            "/api/v1/cart/",
            {"course_id": str(free.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        paid = self.create_course(is_free=False)
        self.client.post(
            "/api/v1/cart/",
            {"course_id": str(paid.id)},
            format="json",
        )
        self.client.post("/api/v1/cart/checkout/", {}, format="json")
        response = self.client.post(
            "/api/v1/cart/",
            {"course_id": str(paid.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DirectMessageAndActivityTests(Team8APITestCase):
    def test_direct_message_thread_send_list_and_read(self):
        sent = self.client.post(
            "/api/v1/messages/with/2/",
            {"body": "سلام مربی، برای شروع آماده‌ام."},
            format="json",
        )
        self.assertEqual(sent.status_code, status.HTTP_201_CREATED)
        self.assertTrue(sent.data["mine"])

        self.authenticate(2, "coach")
        thread = self.client.get("/api/v1/messages/with/1/")
        self.assertEqual(thread.status_code, status.HTTP_200_OK)
        self.assertEqual(thread.data["messages"][0]["body"], sent.data["body"])
        message = DirectMessage.objects.get(pk=sent.data["id"])
        self.assertTrue(message.is_read)

        threads = self.client.get("/api/v1/messages/")
        self.assertEqual(threads.data[0]["profile"]["user_id"], 1)

    def test_cannot_message_self(self):
        response = self.client.post(
            "/api/v1/messages/with/1/",
            {"body": "self"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activity_contains_openable_follow_and_message(self):
        Follow.objects.create(follower_id=2, following_id=1)
        DirectMessage.objects.create(
            sender_id=2,
            sender_username="coach",
            recipient_id=1,
            recipient_username="amir",
            body="یک پیام تست",
        )

        response = self.client.get("/api/v1/activity/?scope=notifications")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = {item["type"] for item in response.data}
        self.assertIn("follow", types)
        self.assertIn("message", types)
        self.assertTrue(all(item["target_page"] for item in response.data))
