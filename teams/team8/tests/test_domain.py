from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase

from ..models import (
    Category,
    Comment,
    Course,
    Enrollment,
    Follow,
    Lesson,
    LessonProgress,
    Post,
    UserProfile,
)
from ..services import ensure_profile, sync_tags, unique_slug
from ..validators import validate_image, validate_list, validate_video


class DomainModelTests(TestCase):
    def test_soft_delete_manager_and_hard_delete(self):
        profile = UserProfile.objects.create(user_id=10, username="soft")
        profile.delete()
        self.assertFalse(UserProfile.objects.filter(pk=profile.pk).exists())
        self.assertTrue(UserProfile.all_objects.get(pk=profile.pk).is_deleted)
        profile.hard_delete()
        self.assertFalse(UserProfile.all_objects.filter(pk=profile.pk).exists())

    def test_ensure_profile_syncs_gateway_identity(self):
        profile, created = ensure_profile(SimpleNamespace(id=12, username="first"))
        self.assertTrue(created)
        profile.delete()
        profile, created = ensure_profile(SimpleNamespace(id=12, username="renamed"))
        self.assertFalse(created)
        self.assertFalse(profile.is_deleted)
        self.assertEqual(profile.username, "renamed")

    def test_unique_slug_and_tag_sync_are_deterministic(self):
        root = Category.objects.create(name="Fitness", slug="fitness")
        self.assertEqual(unique_slug(Category, "Fitness"), "fitness-2")
        course = Course.objects.create(
            author_id=1,
            author_username="coach",
            title="Course",
            slug="course",
            description="description",
            category=root,
        )
        sync_tags(course, [" strength ", "strength", "mobility"])
        self.assertEqual(set(course.tags.values_list("name", flat=True)), {"strength", "mobility"})
        sync_tags(course, ["strength"])
        self.assertEqual(list(course.tags.values_list("name", flat=True)), ["strength"])
        sync_tags(course, ["strength", "mobility"])
        self.assertEqual(set(course.tags.values_list("name", flat=True)), {"strength", "mobility"})

    def test_category_rejects_parent_cycle(self):
        parent = Category.objects.create(name="Parent", slug="parent")
        child = Category.objects.create(name="Child", slug="child", parent=parent)
        parent.parent = child
        with self.assertRaises(ValidationError):
            parent.full_clean()

    def test_comment_rejects_parent_from_other_post(self):
        first = Post.objects.create(author_id=1, author_username="a", body="first")
        second = Post.objects.create(author_id=2, author_username="b", body="second")
        parent = Comment.objects.create(
            post=first,
            user_id=1,
            username="a",
            text="parent",
        )
        reply = Comment(
            post=second,
            user_id=2,
            username="b",
            parent=parent,
            text="reply",
        )
        with self.assertRaises(ValidationError):
            reply.full_clean()

    def test_enrollment_and_progress_validate_course_consistency(self):
        category = Category.objects.create(name="Fitness", slug="fitness")
        first = Course.objects.create(
            author_id=1,
            author_username="a",
            title="First",
            slug="first",
            description="d",
            category=category,
        )
        second = Course.objects.create(
            author_id=1,
            author_username="a",
            title="Second",
            slug="second",
            description="d",
            category=category,
        )
        first_lesson = Lesson.objects.create(course=first, title="one", order=1)
        second_lesson = Lesson.objects.create(course=second, title="two", order=1)
        enrollment = Enrollment(user_id=1, course=first, current_lesson=second_lesson)
        with self.assertRaises(ValidationError):
            enrollment.full_clean()
        enrollment.current_lesson = first_lesson
        enrollment.save()
        progress = LessonProgress(enrollment=enrollment, lesson=second_lesson)
        with self.assertRaises(ValidationError):
            progress.full_clean()

    def test_file_and_json_validators(self):
        validate_image(SimpleUploadedFile("valid.webp", b"image"))
        validate_video(SimpleUploadedFile("valid.mp4", b"video"))
        validate_list([{"valid": True}])
        with self.assertRaises(ValidationError):
            validate_image(SimpleUploadedFile("bad.gif", b"image"))
        with self.assertRaises(ValidationError):
            validate_video(SimpleUploadedFile("bad.avi", b"video"))
        with self.assertRaises(ValidationError):
            validate_list({"invalid": True})

    def test_follow_database_constraint_prevents_self_follow(self):
        follow = Follow(follower_id=1, following_id=1)
        with self.assertRaises(ValidationError):
            follow.full_clean()

    def test_demo_seed_is_complete_and_idempotent(self):
        call_command("seed_demo", verbosity=0)
        counts = {
            "profiles": UserProfile.objects.count(),
            "posts": Post.objects.count(),
            "courses": Course.objects.count(),
            "lessons": Lesson.objects.count(),
        }
        call_command("seed_demo", verbosity=0)
        self.assertEqual(
            counts,
            {
                "profiles": UserProfile.objects.count(),
                "posts": Post.objects.count(),
                "courses": Course.objects.count(),
                "lessons": Lesson.objects.count(),
            },
        )
        self.assertGreaterEqual(counts["profiles"], 3)
        self.assertGreaterEqual(counts["posts"], 2)
        self.assertGreaterEqual(counts["lessons"], 4)
