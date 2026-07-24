import json
import tempfile
from base64 import b64decode
from pathlib import Path
from urllib.parse import quote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from ..models import (
    Comment,
    Follow,
    Like,
    OutboxEvent,
    Post,
    PostReport,
    PostStatus,
    PostType,
    UserProfile,
    WorkoutRecord,
)
from .common import Team8APITestCase


class IdentityTests(Team8APITestCase):
    def test_health_is_public(self):
        self.client.credentials()
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["service"], "polylife-team8")

    def test_protected_api_requires_gateway_headers(self):
        self.client.credentials()
        response = self.client.get("/api/whoami")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["success"], False)

    def test_invalid_gateway_principal_is_rejected(self):
        self.authenticate(user_id=-2, username="invalid")
        response = self.client.get("/api/whoami")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forged_identity_headers_without_gateway_secret_are_rejected(self):
        self.client.credentials(
            HTTP_X_USER_ID="1",
            HTTP_X_USER_USERNAME="amir",
        )
        response = self.client.get("/api/whoami")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_whoami_creates_and_resurrects_profile(self):
        self.athlete.delete()
        response = self.client.get("/api/whoami")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["username"], "amir")
        self.assertFalse(UserProfile.all_objects.get(user_id=1).is_deleted)

    def test_percent_encoded_unicode_username_from_core_is_decoded(self):
        self.authenticate(user_id=5, username=quote("امیر"))
        response = self.client.get("/api/whoami")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "امیر")
        self.assertEqual(UserProfile.objects.get(user_id=5).username, "امیر")

    def test_profile_update_search_and_role_filter(self):
        response = self.client.patch(
            "/api/v1/profiles/me/",
            {"bio": "Student athlete", "location": "Tehran", "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.role, "athlete")

        response = self.client.patch(
            "/api/v1/profiles/me/",
            {"bio": "Student athlete", "location": "Tehran", "role": "coach"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "coach")
        self.assertFalse(response.data["is_verified"])

        self.athlete.is_verified = True
        self.athlete.save(update_fields=["is_verified", "updated_at"])
        response = self.client.patch(
            "/api/v1/profiles/me/",
            {"role": "nutrition_specialist"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get("/api/v1/profiles/?q=Sara&role=coach")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.items(response)[0]["user_id"], 2)

    def test_profile_avatar_can_be_uploaded(self):
        png = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0"
            "lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(
            MEDIA_ROOT=temp_dir
        ):
            response = self.client.patch(
                "/api/v1/profiles/me/",
                {"avatar": SimpleUploadedFile("avatar.png", png, "image/png")},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("/media/avatars/", response.data["avatar_url"])

    def test_follow_unfollow_and_relationship_lists(self):
        response = self.client.post("/api/v1/profiles/2/follow/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Follow.objects.filter(follower_id=1, following_id=2).exists())
        followers = self.client.get("/api/v1/profiles/2/followers/")
        following = self.client.get("/api/v1/profiles/1/following/")
        self.assertEqual(self.items(followers)[0]["user_id"], 1)
        self.assertEqual(self.items(following)[0]["user_id"], 2)
        response = self.client.delete("/api/v1/profiles/2/follow/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Follow.objects.filter(follower_id=1, following_id=2).exists())

    def test_self_follow_is_rejected(self):
        response = self.client.post("/api/v1/profiles/1/follow/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_spa_asset_is_served_with_cache_headers_and_confined(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir()
            (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
            with override_settings(FRONTEND_DIST=root):
                response = self.client.get("/assets/app.js")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn("immutable", response["Cache-Control"])
                self.assertEqual(b"".join(response.streaming_content), b"console.log('ok')")
                response = self.client.get("/assets/missing.js")
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SocialApiTests(Team8APITestCase):
    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_create_general_post_and_outbox(self):
        response = self.client.post(
            "/api/v1/posts/",
            {"body": "My daily progress", "post_type": "general", "status": "published"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"]["user_id"], 1)
        self.assertTrue(
            OutboxEvent.objects.filter(
                event_type="post.published",
                aggregate_id=response.data["id"],
            ).exists()
        )

    def test_progress_chart_can_be_shared_as_an_image_post(self):
        png = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0"
            "lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(
            MEDIA_ROOT=temp_dir
        ):
            response = self.client.post(
                "/api/v1/posts/",
                {
                    "body": "نمودار پیشرفت این ماه",
                    "post_type": "progress",
                    "status": "published",
                    "media": SimpleUploadedFile("progress.png", png, "image/png"),
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["post_type"], "progress")
            self.assertIn("/media/posts/", response.data["media_url"])

    def test_workout_post_accepts_nested_json_in_multipart(self):
        response = self.client.post(
            "/api/v1/posts/",
            {
                "body": "Bench press",
                "post_type": "workout",
                "status": "published",
                "workout": json.dumps(
                    {"exercise_type": "Bench press", "weight_kg": 80, "repetitions": 8}
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["workout"]["repetitions"], 8)
        self.assertTrue(WorkoutRecord.objects.filter(post_id=response.data["id"]).exists())

    def test_workout_without_record_is_invalid(self):
        response = self.client.post(
            "/api/v1/posts/",
            {"body": "Incomplete", "post_type": "workout"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_workout_can_be_removed_and_recreated(self):
        response = self.client.post(
            "/api/v1/posts/",
            {
                "body": "Workout",
                "post_type": "workout",
                "workout": {
                    "exercise_type": "Squat",
                    "weight_kg": 60,
                    "repetitions": 10,
                },
            },
            format="json",
        )
        post_id = response.data["id"]
        response = self.client.patch(
            f"/api/v1/posts/{post_id}/",
            {"post_type": "general"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["workout"])
        response = self.client.patch(
            f"/api/v1/posts/{post_id}/",
            {
                "post_type": "workout",
                "workout": {
                    "exercise_type": "Deadlift",
                    "weight_kg": 90,
                    "repetitions": 5,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["workout"]["exercise_type"], "Deadlift")
        self.assertEqual(WorkoutRecord.all_objects.filter(post_id=post_id).count(), 1)

    def test_feed_contains_self_and_followed_but_not_strangers(self):
        own = self.create_post(1, "amir", "own")
        followed = self.create_post(2, "coach", "followed")
        stranger = self.create_post(4, "stranger", "stranger")
        Follow.objects.create(follower_id=1, following_id=2)
        response = self.client.get("/api/v1/posts/feed/")
        ids = {item["id"] for item in self.items(response)}
        self.assertIn(str(own.id), ids)
        self.assertIn(str(followed.id), ids)
        self.assertNotIn(str(stranger.id), ids)

    def test_explore_search_like_and_unlike(self):
        post = self.create_post(body="Unique deadlift record")
        response = self.client.get("/api/v1/posts/explore/?q=deadlift")
        self.assertEqual(self.items(response)[0]["id"], str(post.id))
        response = self.client.post(f"/api/v1/posts/{post.id}/like/", {}, format="json")
        self.assertTrue(response.data["liked"])
        self.assertEqual(response.data["like_count"], 1)
        self.assertTrue(Like.objects.filter(post=post, user_id=1).exists())
        response = self.client.delete(f"/api/v1/posts/{post.id}/like/")
        self.assertFalse(response.data["liked"])
        self.assertEqual(response.data["like_count"], 0)

    def test_comments_and_threaded_replies(self):
        post = self.create_post()
        root = self.client.post(
            f"/api/v1/posts/{post.id}/comments/",
            {"text": "Great"},
            format="json",
        )
        self.assertEqual(root.status_code, status.HTTP_201_CREATED)
        reply = self.client.post(
            f"/api/v1/posts/{post.id}/comments/",
            {"text": "Thanks", "parent_id": root.data["id"]},
            format="json",
        )
        self.assertEqual(reply.status_code, status.HTTP_201_CREATED)
        response = self.client.get(f"/api/v1/posts/{post.id}/comments/")
        self.assertEqual(response.data[0]["replies"][0]["text"], "Thanks")
        self.assertEqual(Comment.objects.count(), 2)

    def test_parent_comment_must_belong_to_same_post(self):
        first = self.create_post(body="first")
        second = self.create_post(body="second")
        parent = Comment.objects.create(
            post=first,
            user_id=1,
            username="amir",
            text="parent",
        )
        response = self.client.post(
            f"/api/v1/posts/{second.id}/comments/",
            {"text": "invalid reply", "parent_id": str(parent.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_is_unique_and_three_reports_flag_post(self):
        post = self.create_post()
        response = self.client.post(
            f"/api/v1/posts/{post.id}/report/",
            {"reason": "Spam"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        duplicate = self.client.post(
            f"/api/v1/posts/{post.id}/report/",
            {"reason": "Again"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        for user_id in (3, 4):
            self.authenticate(user_id, f"user{user_id}")
            self.client.post(
                f"/api/v1/posts/{post.id}/report/",
                {"reason": "Unsafe"},
                format="json",
            )
        post.refresh_from_db()
        self.assertEqual(post.status, PostStatus.REPORTED)
        self.assertEqual(PostReport.objects.filter(post=post).count(), 3)

    def test_non_owner_cannot_edit_or_delete_post(self):
        post = self.create_post(author_id=2)
        response = self.client.patch(
            f"/api/v1/posts/{post.id}/",
            {"body": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f"/api/v1/posts/{post.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(pk=post.id).exists())

    def test_owner_can_edit_and_soft_delete_post(self):
        post = self.create_post(author_id=1, username="amir")
        response = self.client.patch(
            f"/api/v1/posts/{post.id}/",
            {"body": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["body"], "Updated")
        response = self.client.delete(f"/api/v1/posts/{post.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=post.id).exists())
        self.assertTrue(Post.all_objects.get(pk=post.id).is_deleted)

    def test_drafts_are_only_visible_to_owner(self):
        draft = Post.objects.create(
            author_id=2,
            author_username="coach",
            body="private draft",
            status=PostStatus.DRAFT,
            post_type=PostType.GENERAL,
            published_at=timezone.now(),
        )
        response = self.client.get(f"/api/v1/posts/{draft.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.authenticate(2, "coach")
        response = self.client.get(f"/api/v1/posts/{draft.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
