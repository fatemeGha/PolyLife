"""Transactional domain services shared by API endpoints and tests."""

from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, When
from django.utils import timezone
from django.utils.text import slugify

from .models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Follow,
    Like,
    LessonProgress,
    OutboxEvent,
    Post,
    PostStatus,
    Purchase,
    PurchaseStatus,
    Tag,
    UserProfile,
)

FEED_CACHE_TTL = 60


def ensure_profile(principal):
    profile, created = UserProfile.all_objects.get_or_create(
        user_id=principal.id,
        defaults={
            "username": principal.username,
            "display_name": principal.username,
            "is_deleted": False,
        },
    )
    changed_fields = []
    if profile.is_deleted:
        profile.is_deleted = False
        changed_fields.append("is_deleted")
    if profile.username != principal.username:
        profile.username = principal.username
        changed_fields.append("username")
    if changed_fields:
        profile.save(update_fields=[*changed_fields, "updated_at"])
    return profile, created


def unique_slug(model, value, instance=None):
    base = slugify(value, allow_unicode=True)[:220] or "item"
    candidate = base
    counter = 2
    queryset = model.all_objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[: 260 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


def sync_tags(instance, names):
    clean_names = sorted({name.strip()[:60] for name in names if name.strip()})
    tags = []
    for name in clean_names:
        tag, _ = Tag.all_objects.get_or_create(
            name=name,
            defaults={"slug": unique_slug(Tag, name), "is_deleted": False},
        )
        if tag.is_deleted:
            tag.is_deleted = False
            tag.save(update_fields=["is_deleted", "updated_at"])
        tags.append(tag)

    manager = instance.tags
    through = manager.through
    source_field = manager.source_field_name
    target_field = manager.target_field_name
    relations = {
        getattr(relation, f"{target_field}_id"): relation
        for relation in through.all_objects.filter(**{source_field: instance})
    }
    desired_ids = {tag.id for tag in tags}

    for tag in tags:
        relation = relations.get(tag.id)
        if relation:
            if relation.is_deleted:
                relation.is_deleted = False
                relation.save(update_fields=["is_deleted", "updated_at"])
        else:
            through.objects.create(
                **{
                    source_field: instance,
                    target_field: tag,
                }
            )

    for tag_id, relation in relations.items():
        if tag_id not in desired_ids and not relation.is_deleted:
            # A soft-deleted explicit through row still participates in Django's
            # SQL JOIN, so removing a membership must delete that link physically.
            relation.hard_delete()


def create_outbox_event(event_type, aggregate, payload):
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate.__class__.__name__,
        aggregate_id=aggregate.pk,
        payload=payload,
    )


def invalidate_user_feed(user_id):
    cache.delete(f"feed:{user_id}")


def invalidate_author_audience(author_id):
    invalidate_user_feed(author_id)
    follower_ids = Follow.objects.filter(following_id=author_id).values_list(
        "follower_id", flat=True
    )
    for follower_id in follower_ids:
        invalidate_user_feed(follower_id)


def feed_for(user_id):
    cache_key = f"feed:{user_id}"
    cached_ids = cache.get(cache_key)
    if cached_ids is None:
        following_ids = list(
            Follow.objects.filter(follower_id=user_id).values_list(
                "following_id", flat=True
            )
        )
        author_ids = [user_id, *following_ids]
        cached_ids = list(
            Post.objects.filter(
                author_id__in=author_ids,
                status=PostStatus.PUBLISHED,
            )
            .order_by("-published_at", "-created_at")
            .values_list("id", flat=True)[:200]
        )
        cache.set(cache_key, [str(value) for value in cached_ids], FEED_CACHE_TTL)

    if not cached_ids:
        return Post.objects.none()

    positions = {str(post_id): index for index, post_id in enumerate(cached_ids)}
    preserved_order = Case(
        *[
            When(pk=post_id, then=position)
            for post_id, position in positions.items()
        ],
        output_field=IntegerField(),
    )
    return (
        Post.objects.filter(id__in=cached_ids)
        .select_related("workout")
        .annotate(
            like_count_value=Count(
                "likes",
                filter=Q(likes__is_deleted=False),
                distinct=True,
            ),
            comment_count_value=Count(
                "comments",
                filter=Q(comments__is_deleted=False),
                distinct=True,
            ),
            liked_by_me_value=Exists(
                Like.objects.filter(
                    post_id=OuterRef("pk"),
                    user_id=user_id,
                    is_deleted=False,
                )
            ),
        )
        .order_by(preserved_order)
    )


@transaction.atomic
def enroll_user(principal, course):
    if course.status != "published":
        raise ValueError("ثبت‌نام فقط در دوره منتشرشده امکان‌پذیر است.")
    if not course.is_free and not Purchase.objects.filter(
        user_id=principal.id,
        course=course,
        status=PurchaseStatus.COMPLETED,
    ).exists():
        raise ValueError("برای شروع این دوره ابتدا باید خرید را تکمیل کنید.")

    first_lesson = course.lessons.first()
    enrollment, created = Enrollment.all_objects.get_or_create(
        user_id=principal.id,
        course=course,
        defaults={
            "status": EnrollmentStatus.ACTIVE,
            "current_lesson": first_lesson,
            "is_deleted": False,
        },
    )
    if enrollment.is_deleted or enrollment.status == EnrollmentStatus.CANCELLED:
        enrollment.is_deleted = False
        enrollment.status = EnrollmentStatus.ACTIVE
        enrollment.current_lesson = first_lesson
        enrollment.completed_at = None
        enrollment.save()
        created = True

    if created:
        LessonProgress.objects.bulk_create(
            [
                LessonProgress(enrollment=enrollment, lesson=lesson)
                for lesson in course.lessons.all()
            ],
            ignore_conflicts=True,
        )
        create_outbox_event(
            "course.enrolled",
            enrollment,
            {
                "user_id": principal.id,
                "username": principal.username,
                "course_id": str(course.id),
            },
        )
    return enrollment, created


@transaction.atomic
def update_lesson_progress(enrollment, lesson, watched_seconds, completed):
    if lesson.course_id != enrollment.course_id:
        raise ValueError("این درس متعلق به دوره ثبت‌نام‌شده نیست.")

    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
    )
    progress.watched_seconds = max(progress.watched_seconds, watched_seconds or 0)
    if completed:
        progress.is_completed = True
        progress.completed_at = progress.completed_at or timezone.now()
    progress.save()

    lesson_count = enrollment.course.lessons.count()
    completed_count = enrollment.lesson_progress.filter(is_completed=True).count()
    percent = round((completed_count / lesson_count) * 100) if lesson_count else 0
    enrollment.progress_percent = percent
    if percent >= 100:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
    elif completed_count:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
        next_progress = (
            enrollment.lesson_progress.filter(is_completed=False)
            .select_related("lesson")
            .order_by("lesson__order")
            .first()
        )
        enrollment.current_lesson = next_progress.lesson if next_progress else lesson
    enrollment.save()
    return progress, enrollment
