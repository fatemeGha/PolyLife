"""API serializers for the social-network and LMS domains."""

import json

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from rest_framework import serializers

from .models import (
    CartItem,
    Category,
    Comment,
    Content,
    ContentRating,
    ContentStatus,
    ContentType,
    Course,
    CourseStatus,
    DietPlan,
    DirectMessage,
    Enrollment,
    EnrollmentStatus,
    Follow,
    Lesson,
    LessonProgress,
    Like,
    Post,
    PostReport,
    PostStatus,
    PostType,
    Purchase,
    PurchaseStatus,
    Tag,
    TrainingPlan,
    UserProfile,
    UserRole,
    WorkoutRecord,
)
from .services import (
    create_outbox_event,
    ensure_profile,
    invalidate_author_audience,
    sync_tags,
    unique_slug,
)


def _decode_json_fields(data, *field_names):
    """Decode JSON values submitted as strings in multipart forms."""
    if hasattr(data, "lists"):
        mutable = {
            key: values[-1] if len(values) == 1 else values
            for key, values in data.lists()
        }
    else:
        mutable = data.copy()
    for field_name in field_names:
        value = mutable.get(field_name)
        if not isinstance(value, str):
            continue
        try:
            mutable[field_name] = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError(
                {field_name: "ساختار JSON این فیلد معتبر نیست."}
            ) from exc
    return mutable


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()


class UserProfileSummarySerializer(serializers.ModelSerializer):
    badge = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "user_id",
            "username",
            "display_name",
            "role",
            "specialization",
            "avatar_url",
            "is_verified",
            "badge",
        ]

    def get_avatar_url(self, obj) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url


class UserProfileSerializer(UserProfileSummarySerializer):
    avatar = serializers.ImageField(write_only=True, required=False, allow_null=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta(UserProfileSummarySerializer.Meta):
        fields = [
            *UserProfileSummarySerializer.Meta.fields,
            "avatar",
            "bio",
            "location",
            "experience_years",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user_id",
            "username",
            "is_verified",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "created_at",
            "updated_at",
        ]

    def validate_role(self, value):
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("نقش مدیر فقط توسط مدیریت سامانه تعیین می‌شود.")
        if self.instance and self.instance.is_verified and value != self.instance.role:
            raise serializers.ValidationError(
                "نقش پروفایل تأییدشده فقط توسط مدیریت سامانه تغییر می‌کند."
            )
        return value

    def get_followers_count(self, obj) -> int:
        return Follow.objects.filter(following_id=obj.user_id).count()

    def get_following_count(self, obj) -> int:
        return Follow.objects.filter(follower_id=obj.user_id).count()

    def get_posts_count(self, obj) -> int:
        return Post.objects.filter(
            author_id=obj.user_id,
            status=PostStatus.PUBLISHED,
        ).count()

    def get_is_following(self, obj) -> bool:
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(
                follower_id=request.user.id,
                following_id=obj.user_id,
            ).exists()
        )


class WorkoutRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutRecord
        fields = [
            "exercise_type",
            "weight_kg",
            "repetitions",
            "duration_seconds",
        ]

    def validate(self, attrs):
        values = (
            attrs.get("weight_kg", getattr(self.instance, "weight_kg", None)),
            attrs.get("repetitions", getattr(self.instance, "repetitions", None)),
            attrs.get(
                "duration_seconds",
                getattr(self.instance, "duration_seconds", None),
            ),
        )
        if not any(value is not None and value > 0 for value in values):
            raise serializers.ValidationError(
                "حداقل یکی از وزن، تعداد تکرار یا مدت تمرین را وارد کنید."
            )
        return attrs


class PostReadSerializer(serializers.ModelSerializer):
    workout = WorkoutRecordSerializer(read_only=True)
    author = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author_id",
            "author_username",
            "author",
            "body",
            "media_url",
            "post_type",
            "status",
            "workout",
            "like_count",
            "comment_count",
            "liked_by_me",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def get_author(self, obj) -> dict:
        profile_cache = self.context.setdefault("_profile_cache", {})
        if obj.author_id not in profile_cache:
            profile_cache[obj.author_id] = UserProfile.objects.filter(
                user_id=obj.author_id
            ).first()
        profile = profile_cache[obj.author_id]
        return (
            UserProfileSummarySerializer(profile, context=self.context).data
            if profile
            else {
                "user_id": obj.author_id,
                "username": obj.author_username,
                "display_name": obj.author_username,
            }
        )

    def get_media_url(self, obj) -> str | None:
        if not obj.media:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.media.url) if request else obj.media.url

    def get_like_count(self, obj) -> int:
        if hasattr(obj, "like_count_value"):
            return obj.like_count_value
        return obj.likes.filter(is_deleted=False).count()

    def get_comment_count(self, obj) -> int:
        if hasattr(obj, "comment_count_value"):
            return obj.comment_count_value
        return obj.comments.filter(is_deleted=False).count()

    def get_liked_by_me(self, obj) -> bool:
        if hasattr(obj, "liked_by_me_value"):
            return obj.liked_by_me_value
        request = self.context.get("request")
        return bool(
            request
            and Like.objects.filter(post=obj, user_id=request.user.id).exists()
        )


class PostWriteSerializer(serializers.ModelSerializer):
    workout = WorkoutRecordSerializer(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = ["body", "media", "post_type", "status", "workout"]

    def to_internal_value(self, data):
        return super().to_internal_value(_decode_json_fields(data, "workout"))

    def validate_status(self, value):
        if value not in {PostStatus.DRAFT, PostStatus.PUBLISHED}:
            raise serializers.ValidationError("وضعیت انتخاب‌شده برای کاربر مجاز نیست.")
        return value

    def validate(self, attrs):
        post_type = attrs.get(
            "post_type",
            getattr(self.instance, "post_type", PostType.GENERAL),
        )
        workout = attrs.get("workout")
        has_existing_workout = bool(
            self.instance
            and WorkoutRecord.objects.filter(post=self.instance).exists()
        )
        if post_type == PostType.WORKOUT and not (workout or has_existing_workout):
            raise serializers.ValidationError(
                {"workout": "اطلاعات رکورد ورزشی الزامی است."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        ensure_profile(request.user)
        workout_data = validated_data.pop("workout", None)
        if validated_data.get("status", PostStatus.PUBLISHED) == PostStatus.PUBLISHED:
            validated_data["published_at"] = timezone.now()
        post = Post.objects.create(
            author_id=request.user.id,
            author_username=request.user.username,
            **validated_data,
        )
        if workout_data:
            WorkoutRecord.objects.create(post=post, **workout_data)
        create_outbox_event(
            "post.published" if post.status == PostStatus.PUBLISHED else "post.created",
            post,
            {
                "author_id": request.user.id,
                "author_username": request.user.username,
                "post_type": post.post_type,
            },
        )
        invalidate_author_audience(post.author_id)
        return post

    @transaction.atomic
    def update(self, instance, validated_data):
        workout_data = validated_data.pop("workout", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if instance.status == PostStatus.PUBLISHED and not instance.published_at:
            instance.published_at = timezone.now()
        instance.save()

        if instance.post_type == PostType.WORKOUT and workout_data is not None:
            workout = WorkoutRecord.all_objects.filter(post=instance).first()
            if workout:
                workout.is_deleted = False
            else:
                workout = WorkoutRecord(post=instance)
            for field, value in workout_data.items():
                setattr(workout, field, value)
            workout.full_clean()
            workout.save()
        elif instance.post_type != PostType.WORKOUT:
            existing = WorkoutRecord.all_objects.filter(post=instance).first()
            if existing:
                # A reverse one-to-one JOIN does not apply the related manager's
                # soft-delete filter; remove this dependent value completely.
                existing.hard_delete()
                instance._state.fields_cache.pop("workout", None)
        invalidate_author_audience(instance.author_id)
        return instance


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "user_id",
            "username",
            "parent",
            "text",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "post",
            "user_id",
            "username",
            "replies",
            "created_at",
            "updated_at",
        ]

    def get_replies(self, obj) -> list:
        if obj.parent_id:
            return []
        return CommentSerializer(
            obj.replies.filter(is_deleted=False),
            many=True,
            context=self.context,
        ).data


class CommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1500)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class DirectMessageSerializer(serializers.ModelSerializer):
    mine = serializers.SerializerMethodField()

    class Meta:
        model = DirectMessage
        fields = [
            "id",
            "sender_id",
            "sender_username",
            "recipient_id",
            "recipient_username",
            "body",
            "is_read",
            "read_at",
            "mine",
            "created_at",
        ]
        read_only_fields = fields

    def get_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)


class DirectMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=3000, trim_whitespace=True)


class ActivityItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    created_at = serializers.DateTimeField()
    target_page = serializers.CharField()
    target_id = serializers.CharField(allow_null=True)
    actor = UserProfileSummarySerializer(allow_null=True)
    unread = serializers.BooleanField()


class PostReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostReport
        fields = ["id", "post", "reporter_id", "reason", "status", "created_at"]
        read_only_fields = ["id", "post", "reporter_id", "status", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    full_path = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "full_path",
            "children_count",
            "created_at",
        ]
        read_only_fields = ["slug", "full_path", "children_count", "created_at"]

    def get_full_path(self, obj) -> str:
        names = [obj.name]
        parent = obj.parent
        while parent:
            names.append(parent.name)
            parent = parent.parent
        return " / ".join(reversed(names))

    def get_children_count(self, obj) -> int:
        return obj.children.filter(is_deleted=False).count()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class ContentReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            "id",
            "author_id",
            "author_username",
            "title",
            "slug",
            "content_type",
            "category",
            "body",
            "media_url",
            "thumbnail_url",
            "status",
            "difficulty",
            "duration_minutes",
            "tags",
            "average_rating",
            "rating_count",
            "my_rating",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def get_tags(self, obj) -> list[str]:
        return list(obj.tags.values_list("name", flat=True))

    def _file_url(self, field):
        if not field:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(field.url) if request else field.url

    def get_media_url(self, obj) -> str | None:
        return self._file_url(obj.media)

    def get_thumbnail_url(self, obj) -> str | None:
        return self._file_url(obj.thumbnail)

    def get_average_rating(self, obj) -> float | None:
        if hasattr(obj, "average_rating_value"):
            value = obj.average_rating_value
        else:
            value = obj.ratings.filter(is_deleted=False).aggregate(value=Avg("score"))[
                "value"
            ]
        return round(value, 2) if value is not None else None

    def get_rating_count(self, obj) -> int:
        if hasattr(obj, "rating_count_value"):
            return obj.rating_count_value
        return obj.ratings.filter(is_deleted=False).count()

    def get_my_rating(self, obj) -> int | None:
        if hasattr(obj, "my_rating_value"):
            return obj.my_rating_value
        request = self.context.get("request")
        if not request:
            return None
        return (
            ContentRating.objects.filter(content=obj, user_id=request.user.id)
            .values_list("score", flat=True)
            .first()
        )


class ContentWriteSerializer(serializers.ModelSerializer):
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model = Content
        fields = [
            "title",
            "content_type",
            "category",
            "body",
            "media",
            "thumbnail",
            "status",
            "difficulty",
            "duration_minutes",
            "tag_names",
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(_decode_json_fields(data, "tag_names"))

    def validate_status(self, value):
        if value not in {ContentStatus.DRAFT, ContentStatus.PUBLISHED}:
            raise serializers.ValidationError("فقط ذخیره پیش‌نویس یا انتشار مجاز است.")
        return value

    def validate(self, attrs):
        content_type = attrs.get(
            "content_type",
            getattr(self.instance, "content_type", None),
        )
        status = attrs.get("status", getattr(self.instance, "status", ContentStatus.DRAFT))
        media = attrs.get("media", getattr(self.instance, "media", None))
        if (
            content_type == ContentType.VIDEO
            and status == ContentStatus.PUBLISHED
            and not media
        ):
            raise serializers.ValidationError(
                {"media": "برای انتشار محتوای ویدیویی، فایل MP4 یا WebM لازم است."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        ensure_profile(request.user)
        tag_names = validated_data.pop("tag_names", [])
        validated_data["slug"] = unique_slug(Content, validated_data["title"])
        if validated_data.get("status") == ContentStatus.PUBLISHED:
            validated_data["published_at"] = timezone.now()
        content = Content.objects.create(
            author_id=request.user.id,
            author_username=request.user.username,
            **validated_data,
        )
        sync_tags(content, tag_names)
        create_outbox_event(
            "content.published"
            if content.status == ContentStatus.PUBLISHED
            else "content.draft_saved",
            content,
            {
                "author_id": request.user.id,
                "content_type": content.content_type,
                "category_id": str(content.category_id),
            },
        )
        return content

    @transaction.atomic
    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        if "title" in validated_data and validated_data["title"] != instance.title:
            instance.slug = unique_slug(
                Content,
                validated_data["title"],
                instance=instance,
            )
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if instance.status == ContentStatus.PUBLISHED and not instance.published_at:
            instance.published_at = timezone.now()
        instance.save()
        if tag_names is not None:
            sync_tags(instance, tag_names)
        return instance


class ContentRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentRating
        fields = ["score"]


class LessonSerializer(serializers.ModelSerializer):
    content_title = serializers.CharField(source="content.title", read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "course",
            "title",
            "order",
            "content",
            "content_title",
            "body",
            "duration_minutes",
            "is_preview",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LessonAccessSerializer(serializers.ModelSerializer):
    content_title = serializers.CharField(source="content.title", read_only=True)
    body = serializers.SerializerMethodField()
    content_detail = serializers.SerializerMethodField()
    accessible = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "course",
            "title",
            "order",
            "content",
            "content_title",
            "content_detail",
            "body",
            "duration_minutes",
            "is_preview",
            "accessible",
            "created_at",
            "updated_at",
        ]

    def _accessible(self, obj) -> bool:
        request = self.context.get("request")
        if obj.is_preview:
            return True
        if not request or not request.user.is_authenticated:
            return False
        if obj.course.author_id == request.user.id:
            return True
        cache = self.context.setdefault("_lesson_access_cache", {})
        if obj.course_id not in cache:
            cache[obj.course_id] = (
                Enrollment.objects.filter(
                    user_id=request.user.id,
                    course_id=obj.course_id,
                )
                .exclude(status=EnrollmentStatus.CANCELLED)
                .exists()
            )
        return cache[obj.course_id]

    def get_accessible(self, obj) -> bool:
        return self._accessible(obj)

    def get_body(self, obj) -> str:
        return obj.body if self._accessible(obj) else ""

    def get_content_detail(self, obj) -> dict | None:
        if not obj.content or not self._accessible(obj):
            return None
        return ContentReadSerializer(obj.content, context=self.context).data


class LessonInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["title", "order", "content", "body", "duration_minutes", "is_preview"]


class CourseSummarySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    lesson_count = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    purchased = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "author_username",
            "category_name",
            "difficulty",
            "duration_minutes",
            "is_free",
            "price",
            "purchased",
            "status",
            "lesson_count",
            "cover_url",
            "published_at",
        ]

    def get_cover_url(self, obj) -> str | None:
        if not obj.cover:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.cover.url) if request else obj.cover.url

    def get_lesson_count(self, obj) -> int:
        if hasattr(obj, "lesson_count"):
            return obj.lesson_count
        return obj.lessons.filter(is_deleted=False).count()

    def get_purchased(self, obj) -> bool:
        request = self.context.get("request")
        if not request:
            return False
        cache = self.context.setdefault("_purchase_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = Purchase.objects.filter(
                user_id=request.user.id,
                course=obj,
                status=PurchaseStatus.COMPLETED,
            ).exists()
        return cache[obj.pk]


class CourseReadSerializer(CourseSummarySerializer):
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    lessons = LessonAccessSerializer(many=True, read_only=True)
    enrolled = serializers.SerializerMethodField()
    enrollment_id = serializers.SerializerMethodField()

    class Meta(CourseSummarySerializer.Meta):
        fields = [
            *CourseSummarySerializer.Meta.fields,
            "author_id",
            "description",
            "category",
            "tags",
            "lessons",
            "enrolled",
            "enrollment_id",
            "created_at",
            "updated_at",
        ]

    def get_tags(self, obj) -> list[str]:
        return list(obj.tags.values_list("name", flat=True))

    def _enrollment(self, obj):
        if hasattr(obj, "enrollment_id_value"):
            return obj.enrollment_id_value
        request = self.context.get("request")
        if not request:
            return None
        cache = self.context.setdefault("_enrollment_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = Enrollment.objects.filter(
                user_id=request.user.id,
                course=obj,
            ).first()
        return cache[obj.pk]

    def get_enrolled(self, obj) -> bool:
        return self._enrollment(obj) is not None

    def get_enrollment_id(self, obj) -> str | None:
        enrollment = self._enrollment(obj)
        if not enrollment:
            return None
        return str(getattr(enrollment, "id", enrollment))


class CourseWriteSerializer(serializers.ModelSerializer):
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        default=list,
        write_only=True,
    )
    lessons = LessonInputSerializer(many=True, required=False)

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "category",
            "cover",
            "difficulty",
            "duration_minutes",
            "is_free",
            "price",
            "status",
            "tag_names",
            "lessons",
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(
            _decode_json_fields(data, "tag_names", "lessons")
        )

    def validate_status(self, value):
        if value not in {CourseStatus.DRAFT, CourseStatus.PUBLISHED}:
            raise serializers.ValidationError("فقط پیش‌نویس یا انتشار مجاز است.")
        return value

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", CourseStatus.DRAFT))
        lessons = attrs.get("lessons")
        if lessons:
            orders = [lesson["order"] for lesson in lessons]
            if len(orders) != len(set(orders)):
                raise serializers.ValidationError(
                    {"lessons": "شمارهٔ ترتیب درس‌ها نباید تکراری باشد."}
                )
        existing_lesson_count = self.instance.lessons.count() if self.instance else 0
        effective_lesson_count = (
            len(lessons) if lessons is not None else existing_lesson_count
        )
        if status == CourseStatus.PUBLISHED and effective_lesson_count == 0:
            raise serializers.ValidationError(
                {"lessons": "دوره منتشرشده باید حداقل یک درس داشته باشد."}
            )
        is_free = attrs.get("is_free", getattr(self.instance, "is_free", True))
        price = attrs.get("price", getattr(self.instance, "price", 0))
        if is_free:
            attrs["price"] = 0
        elif not price:
            raise serializers.ValidationError(
                {"price": "برای دوره پولی باید قیمت بیشتر از صفر وارد شود."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        ensure_profile(request.user)
        tag_names = validated_data.pop("tag_names", [])
        lessons_data = validated_data.pop("lessons", [])
        validated_data["slug"] = unique_slug(Course, validated_data["title"])
        if validated_data.get("status") == CourseStatus.PUBLISHED:
            validated_data["published_at"] = timezone.now()
        course = Course.objects.create(
            author_id=request.user.id,
            author_username=request.user.username,
            **validated_data,
        )
        for lesson_data in lessons_data:
            Lesson.objects.create(course=course, **lesson_data)
        if not course.duration_minutes and lessons_data:
            course.duration_minutes = sum(
                lesson.get("duration_minutes", 0) for lesson in lessons_data
            )
            course.save(update_fields=["duration_minutes", "updated_at"])
        sync_tags(course, tag_names)
        create_outbox_event(
            "course.published"
            if course.status == CourseStatus.PUBLISHED
            else "course.draft_saved",
            course,
            {"author_id": request.user.id, "is_free": course.is_free},
        )
        return course

    @transaction.atomic
    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        lessons_data = validated_data.pop("lessons", None)
        if "title" in validated_data and validated_data["title"] != instance.title:
            instance.slug = unique_slug(Course, validated_data["title"], instance=instance)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if instance.status == CourseStatus.PUBLISHED and not instance.published_at:
            instance.published_at = timezone.now()
        instance.save()
        if tag_names is not None:
            sync_tags(instance, tag_names)
        if lessons_data is not None:
            existing_by_order = {
                lesson.order: lesson
                for lesson in Lesson.all_objects.filter(course=instance)
            }
            seen_orders = set()
            for lesson_data in lessons_data:
                order = lesson_data["order"]
                seen_orders.add(order)
                lesson = existing_by_order.get(order)
                if lesson:
                    lesson.is_deleted = False
                    for field, value in lesson_data.items():
                        setattr(lesson, field, value)
                    lesson.save()
                else:
                    Lesson.objects.create(course=instance, **lesson_data)
            for order, lesson in existing_by_order.items():
                if order not in seen_orders:
                    lesson.delete()
            instance.__dict__.pop("lesson_count", None)
        return instance


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson = LessonAccessSerializer(read_only=True)

    class Meta:
        model = LessonProgress
        fields = [
            "id",
            "lesson",
            "watched_seconds",
            "is_completed",
            "completed_at",
            "updated_at",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSummarySerializer(read_only=True)
    current_lesson = LessonAccessSerializer(read_only=True)
    lesson_progress = LessonProgressSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "user_id",
            "course",
            "progress_percent",
            "status",
            "current_lesson",
            "lesson_progress",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "course", "created_at"]


class CartItemCreateSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()


class PurchaseSerializer(serializers.ModelSerializer):
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "course",
            "amount",
            "status",
            "reference",
            "paid_at",
            "created_at",
        ]


class LessonProgressUpdateSerializer(serializers.Serializer):
    watched_seconds = serializers.IntegerField(min_value=0, required=False, default=0)
    is_completed = serializers.BooleanField(required=False, default=False)


class TrainingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPlan
        fields = [
            "id",
            "author_id",
            "author_username",
            "title",
            "description",
            "weeks",
            "exercises",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author_id",
            "author_username",
            "created_at",
            "updated_at",
        ]


class DietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = [
            "id",
            "author_id",
            "author_username",
            "title",
            "description",
            "days",
            "meals",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author_id",
            "author_username",
            "created_at",
            "updated_at",
        ]
