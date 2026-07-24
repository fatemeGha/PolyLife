"""Database model for Microservice 3: internal social network + LMS.

Core users live in a separate database. This service intentionally stores only
their numeric IDs and gateway-provided usernames; it never creates cross-
database foreign keys and never decodes a JWT.
"""

import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone

from .validators import validate_image, validate_list, validate_video


def purchase_reference():
    return f"PL-{uuid.uuid4().hex[:12].upper()}"


class ActiveQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True)

    def hard_delete(self):
        return super().delete()


class ActiveManager(models.Manager):
    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db).filter(is_deleted=False)


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now(), db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_deleted = models.BooleanField(default=False, db_default=False, db_index=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class UserRole(models.TextChoices):
    ATHLETE = "athlete", "ورزشکار"
    COACH = "coach", "مربی"
    SPORTS_DOCTOR = "sports_doctor", "پزشک ورزشی"
    NUTRITION_SPECIALIST = "nutrition_specialist", "متخصص تغذیه"
    ADMIN = "admin", "مدیر"


class UserProfile(BaseModel):
    user_id = models.PositiveBigIntegerField(unique=True)
    username = models.CharField(max_length=150, db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.ATHLETE,
        db_index=True,
    )
    bio = models.TextField(blank=True, max_length=1000)
    specialization = models.CharField(max_length=160, blank=True, db_index=True)
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        validators=[validate_image],
        blank=True,
        null=True,
    )
    location = models.CharField(max_length=120, blank=True)
    experience_years = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(80)],
    )
    is_verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "user_profiles"
        indexes = [
            models.Index(fields=["role", "specialization"], name="profile_role_spec_idx"),
            models.Index(fields=["username", "display_name"], name="profile_search_idx"),
        ]

    @property
    def badge(self):
        badges = {
            UserRole.COACH: "مربی حرفه‌ای",
            UserRole.SPORTS_DOCTOR: "پزشک ورزشی",
            UserRole.NUTRITION_SPECIALIST: "متخصص تغذیه",
            UserRole.ADMIN: "مدیر محتوا",
        }
        return badges.get(self.role, "")

    def __str__(self):
        return self.display_name or self.username


class PostStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    PUBLISHED = "published", "منتشرشده"
    REPORTED = "reported", "گزارش‌شده"
    HIDDEN = "hidden", "مخفی"


class PostType(models.TextChoices):
    GENERAL = "general", "عمومی"
    WORKOUT = "workout", "رکورد ورزشی"
    PROGRESS = "progress", "گزارش پیشرفت"


class Post(BaseModel):
    author_id = models.PositiveBigIntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    body = models.TextField(max_length=5000)
    media = models.ImageField(
        upload_to="posts/%Y/%m/",
        validators=[validate_image],
        blank=True,
        null=True,
    )
    post_type = models.CharField(
        max_length=16,
        choices=PostType.choices,
        default=PostType.GENERAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=PostStatus.choices,
        default=PostStatus.PUBLISHED,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "posts"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["author_id", "status"], name="post_author_status_idx"),
            models.Index(fields=["status", "-published_at"], name="post_feed_idx"),
            models.Index(fields=["post_type", "-created_at"], name="post_type_date_idx"),
        ]

    def __str__(self):
        return f"{self.author_username}: {self.body[:40]}"


class WorkoutRecord(BaseModel):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="workout")
    exercise_type = models.CharField(max_length=120, db_index=True)
    weight_kg = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    repetitions = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "workout_records"
        indexes = [
            models.Index(fields=["exercise_type", "-created_at"], name="workout_ex_date_idx")
        ]

    def clean(self):
        if not any((self.weight_kg, self.repetitions, self.duration_seconds)):
            raise ValidationError("حداقل یکی از وزن، تعداد تکرار یا مدت باید وارد شود.")


class Like(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user_id = models.PositiveBigIntegerField(db_index=True)

    class Meta:
        db_table = "post_likes"
        constraints = [
            models.UniqueConstraint(fields=["post", "user_id"], name="unique_post_like")
        ]
        indexes = [models.Index(fields=["user_id", "-created_at"], name="like_user_date_idx")]


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user_id = models.PositiveBigIntegerField(db_index=True)
    username = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    text = models.TextField(max_length=1500)

    class Meta:
        db_table = "post_comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "parent", "created_at"], name="comment_thread_idx")
        ]

    def clean(self):
        if self.parent_id and self.parent.post_id != self.post_id:
            raise ValidationError("پاسخ باید متعلق به همان پست باشد.")


class Follow(BaseModel):
    follower_id = models.PositiveBigIntegerField(db_index=True)
    following_id = models.PositiveBigIntegerField(db_index=True)

    class Meta:
        db_table = "follows"
        constraints = [
            models.UniqueConstraint(
                fields=["follower_id", "following_id"],
                name="unique_follow_relationship",
            ),
            models.CheckConstraint(
                condition=~Q(follower_id=models.F("following_id")),
                name="prevent_self_follow",
            ),
        ]
        indexes = [
            models.Index(fields=["following_id", "-created_at"], name="followers_idx"),
            models.Index(fields=["follower_id", "-created_at"], name="following_idx"),
        ]


class DirectMessage(BaseModel):
    sender_id = models.PositiveBigIntegerField(db_index=True)
    sender_username = models.CharField(max_length=150)
    recipient_id = models.PositiveBigIntegerField(db_index=True)
    recipient_username = models.CharField(max_length=150)
    body = models.TextField(max_length=3000)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "direct_messages"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(sender_id=models.F("recipient_id")),
                name="prevent_self_message",
            )
        ]
        indexes = [
            models.Index(
                fields=["sender_id", "recipient_id", "-created_at"],
                name="direct_pair_date_idx",
            ),
            models.Index(
                fields=["recipient_id", "is_read", "-created_at"],
                name="direct_unread_idx",
            ),
        ]


class ReportStatus(models.TextChoices):
    OPEN = "open", "باز"
    REVIEWED = "reviewed", "بررسی‌شده"
    DISMISSED = "dismissed", "ردشده"


class PostReport(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reporter_id = models.PositiveBigIntegerField(db_index=True)
    reason = models.CharField(max_length=500)
    status = models.CharField(
        max_length=16,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
        db_index=True,
    )

    class Meta:
        db_table = "post_reports"
        constraints = [
            models.UniqueConstraint(
                fields=["post", "reporter_id"],
                name="unique_post_report",
            )
        ]


class Category(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True, max_length=1000)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="unique_category_sibling")
        ]
        indexes = [models.Index(fields=["parent", "name"], name="category_tree_idx")]

    def clean(self):
        ancestor = self.parent
        while ancestor:
            if ancestor.pk == self.pk:
                raise ValidationError("دسته‌بندی نمی‌تواند زیرمجموعه خودش باشد.")
            ancestor = ancestor.parent

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ContentType(models.TextChoices):
    ARTICLE = "article", "مقاله"
    VIDEO = "video", "ویدیو"
    TRAINING_PLAN = "training_plan", "برنامه تمرینی"
    DIET_PLAN = "diet_plan", "برنامه رژیمی"


class ContentStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    MEDIA_UPLOADING = "media_uploading", "در حال بارگذاری"
    READY = "ready", "آماده انتشار"
    PUBLISHED = "published", "منتشرشده"
    ARCHIVED = "archived", "بایگانی‌شده"
    REJECTED = "rejected", "ردشده"


class DifficultyLevel(models.TextChoices):
    BEGINNER = "beginner", "مبتدی"
    INTERMEDIATE = "intermediate", "متوسط"
    ADVANCED = "advanced", "پیشرفته"


class Content(BaseModel):
    author_id = models.PositiveBigIntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    title = models.CharField(max_length=240, db_index=True)
    slug = models.SlugField(max_length=260, unique=True)
    content_type = models.CharField(
        max_length=24,
        choices=ContentType.choices,
        db_index=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="contents",
    )
    body = models.TextField()
    media = models.FileField(
        upload_to="content/%Y/%m/",
        validators=[validate_video],
        blank=True,
        null=True,
    )
    thumbnail = models.ImageField(
        upload_to="content/thumbnails/%Y/%m/",
        validators=[validate_image],
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=24,
        choices=ContentStatus.choices,
        default=ContentStatus.DRAFT,
        db_index=True,
    )
    difficulty = models.CharField(
        max_length=16,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER,
        db_index=True,
    )
    duration_minutes = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    tags = models.ManyToManyField(Tag, through="ContentTag", related_name="contents")

    class Meta:
        db_table = "contents"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "content_type"], name="content_status_type_idx"),
            models.Index(fields=["category", "difficulty"], name="content_filter_idx"),
            models.Index(fields=["title", "status"], name="content_title_idx"),
        ]

    def __str__(self):
        return self.title


class ContentTag(BaseModel):
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = "content_tags"
        constraints = [
            models.UniqueConstraint(fields=["content", "tag"], name="unique_content_tag")
        ]


class ContentRating(BaseModel):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name="ratings")
    user_id = models.PositiveBigIntegerField(db_index=True)
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        db_table = "content_ratings"
        constraints = [
            models.UniqueConstraint(
                fields=["content", "user_id"],
                name="unique_content_rating",
            )
        ]


class ContentView(BaseModel):
    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="view_history",
    )
    user_id = models.PositiveBigIntegerField(db_index=True)
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "content_views"
        constraints = [
            models.UniqueConstraint(
                fields=["content", "user_id"],
                name="unique_content_viewer",
            )
        ]
        indexes = [
            models.Index(
                fields=["user_id", "-updated_at"],
                name="content_view_user_idx",
            )
        ]


class CourseStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    PUBLISHED = "published", "منتشرشده"
    ARCHIVED = "archived", "بایگانی‌شده"


class Course(BaseModel):
    author_id = models.PositiveBigIntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    title = models.CharField(max_length=240, db_index=True)
    slug = models.SlugField(max_length=260, unique=True)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    cover = models.ImageField(
        upload_to="courses/%Y/%m/",
        validators=[validate_image],
        blank=True,
        null=True,
    )
    difficulty = models.CharField(
        max_length=16,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER,
        db_index=True,
    )
    duration_minutes = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=True, db_index=True)
    price = models.PositiveBigIntegerField(
        default=0,
        help_text="قیمت دوره به تومان؛ برای دوره رایگان صفر است.",
    )
    status = models.CharField(
        max_length=16,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    tags = models.ManyToManyField(Tag, through="CourseTag", related_name="courses")

    class Meta:
        db_table = "courses"
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_free=True, price=0)
                    | Q(is_free=False, price__gt=0)
                ),
                name="course_price_matches_free",
            )
        ]
        indexes = [
            models.Index(fields=["status", "is_free"], name="course_available_idx"),
            models.Index(fields=["category", "difficulty"], name="course_filter_idx"),
        ]

    def __str__(self):
        return self.title


class CourseTag(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = "course_tags"
        constraints = [
            models.UniqueConstraint(fields=["course", "tag"], name="unique_course_tag")
        ]


class CartItem(BaseModel):
    user_id = models.PositiveBigIntegerField(db_index=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="cart_items")

    class Meta:
        db_table = "cart_items"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "course"],
                name="unique_user_cart_course",
            )
        ]


class PurchaseStatus(models.TextChoices):
    COMPLETED = "completed", "پرداخت‌شده"
    REFUNDED = "refunded", "بازگشت وجه"


class Purchase(BaseModel):
    user_id = models.PositiveBigIntegerField(db_index=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="purchases")
    amount = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=PurchaseStatus.choices,
        default=PurchaseStatus.COMPLETED,
        db_index=True,
    )
    reference = models.CharField(
        max_length=32,
        unique=True,
        default=purchase_reference,
        editable=False,
    )
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "purchases"
        ordering = ["-paid_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "course"],
                name="unique_user_course_purchase",
            )
        ]


class Lesson(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=240)
    order = models.PositiveSmallIntegerField()
    content = models.ForeignKey(
        Content,
        on_delete=models.SET_NULL,
        related_name="course_lessons",
        null=True,
        blank=True,
    )
    body = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False)

    class Meta:
        db_table = "lessons"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["course", "order"], name="unique_lesson_order")
        ]
        indexes = [models.Index(fields=["course", "order"], name="lesson_course_order_idx")]

    def __str__(self):
        return f"{self.course.title} — {self.order}. {self.title}"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "ثبت‌نام‌شده"
    IN_PROGRESS = "in_progress", "در حال یادگیری"
    COMPLETED = "completed", "تکمیل‌شده"
    CANCELLED = "cancelled", "لغوشده"


class Enrollment(BaseModel):
    user_id = models.PositiveBigIntegerField(db_index=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="enrollments")
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        max_length=16,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
        db_index=True,
    )
    current_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrollments"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "course"],
                name="unique_course_enrollment",
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="enrollment_user_status_idx")
        ]

    def clean(self):
        if self.current_lesson_id and self.current_lesson.course_id != self.course_id:
            raise ValidationError("درس جاری باید متعلق به همین دوره باشد.")


class LessonProgress(BaseModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    watched_seconds = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lesson_progress"
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"],
                name="unique_lesson_progress",
            )
        ]

    def clean(self):
        if self.enrollment.course_id != self.lesson.course_id:
            raise ValidationError("پیشرفت درس باید متعلق به دوره ثبت‌نام باشد.")


class TrainingPlan(BaseModel):
    author_id = models.PositiveBigIntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    title = models.CharField(max_length=240, db_index=True)
    description = models.TextField(blank=True)
    weeks = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(52)]
    )
    exercises = models.JSONField(default=list, validators=[validate_list])
    is_published = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "training_plans"


class DietPlan(BaseModel):
    author_id = models.PositiveBigIntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    title = models.CharField(max_length=240, db_index=True)
    description = models.TextField(blank=True)
    days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    meals = models.JSONField(default=list, validators=[validate_list])
    is_published = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "diet_plans"


class OutboxStatus(models.TextChoices):
    PENDING = "pending", "در انتظار"
    PUBLISHED = "published", "ارسال‌شده"
    FAILED = "failed", "ناموفق"


class OutboxEvent(BaseModel):
    event_type = models.CharField(max_length=120, db_index=True)
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.UUIDField(db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "outbox_events"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="outbox_pending_idx")
        ]
