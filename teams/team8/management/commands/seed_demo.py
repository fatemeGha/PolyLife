"""Create deterministic, idempotent demo data for the three P2 scenarios."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from teams.team8.models import (
    Category,
    Comment,
    Content,
    ContentRating,
    ContentStatus,
    ContentType,
    ContentView,
    Course,
    CourseStatus,
    DietPlan,
    DifficultyLevel,
    DirectMessage,
    Enrollment,
    EnrollmentStatus,
    Follow,
    Lesson,
    LessonProgress,
    Like,
    Post,
    PostStatus,
    PostType,
    Tag,
    TrainingPlan,
    UserProfile,
    UserRole,
    WorkoutRecord,
)


class Command(BaseCommand):
    help = "Seed Team 8 with idempotent Persian demo content."

    @transaction.atomic
    def handle(self, *args, **options):
        profiles = [
            {
                "user_id": 1,
                "username": "user1",
                "display_name": "امیر ورزشکار",
                "role": UserRole.ATHLETE,
                "bio": "در مسیر ساختن عادت‌های سالم و ثبت رکوردهای تازه.",
                "specialization": "تمرینات قدرتی",
                "location": "تهران",
            },
            {
                "user_id": 2,
                "username": "user2",
                "display_name": "سارا احمدی",
                "role": UserRole.COACH,
                "bio": "مربی بدنسازی و طراح دوره‌های تمرینی مبتدی تا پیشرفته.",
                "specialization": "بدنسازی و اصلاح فرم",
                "experience_years": 8,
                "is_verified": True,
            },
            {
                "user_id": 3,
                "username": "user3",
                "display_name": "دکتر نیلوفر کریمی",
                "role": UserRole.NUTRITION_SPECIALIST,
                "bio": "متخصص تغذیه ورزشی و برنامه‌ریزی وعده‌های سالم.",
                "specialization": "تغذیه ورزشی",
                "experience_years": 6,
                "is_verified": True,
            },
        ]
        for values in profiles:
            user_id = values.pop("user_id")
            profile, _ = UserProfile.all_objects.update_or_create(
                user_id=user_id,
                defaults={**values, "is_deleted": False},
            )
            self.stdout.write(f"profile: {profile.username}")

        sport, _ = Category.all_objects.update_or_create(
            slug="sport",
            defaults={
                "name": "ورزش",
                "description": "آموزش‌ها و دوره‌های ورزشی",
                "is_deleted": False,
            },
        )
        strength, _ = Category.all_objects.update_or_create(
            slug="strength-training",
            defaults={
                "name": "بدنسازی",
                "description": "تمرین مقاومتی و کار با وزنه",
                "parent": sport,
                "is_deleted": False,
            },
        )
        nutrition, _ = Category.all_objects.update_or_create(
            slug="nutrition",
            defaults={
                "name": "تغذیه",
                "description": "رژیم و تغذیه سالم",
                "is_deleted": False,
            },
        )

        for name, slug in [
            ("مبتدی", "beginner"),
            ("گرم‌کردن", "warm-up"),
            ("بدنسازی", "bodybuilding"),
            ("تغذیه سالم", "healthy-nutrition"),
        ]:
            Tag.all_objects.update_or_create(
                slug=slug,
                defaults={"name": name, "is_deleted": False},
            )

        post, _ = Post.all_objects.update_or_create(
            author_id=1,
            body="رکورد تازه پرس سینه؛ استمرار از سنگینی وزنه مهم‌تر است.",
            defaults={
                "author_username": "user1",
                "post_type": PostType.WORKOUT,
                "status": PostStatus.PUBLISHED,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        WorkoutRecord.all_objects.update_or_create(
            post=post,
            defaults={
                "exercise_type": "پرس سینه",
                "weight_kg": 80,
                "repetitions": 5,
                "duration_seconds": 150,
                "is_deleted": False,
            },
        )
        second_post, _ = Post.all_objects.update_or_create(
            author_id=2,
            body="پیش از تمرین قدرتی، گرم‌کردن پویا را جدی بگیرید.",
            defaults={
                "author_username": "user2",
                "post_type": PostType.GENERAL,
                "status": PostStatus.PUBLISHED,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        Follow.all_objects.update_or_create(
            follower_id=1,
            following_id=2,
            defaults={"is_deleted": False},
        )
        Follow.all_objects.update_or_create(
            follower_id=3,
            following_id=2,
            defaults={"is_deleted": False},
        )
        Like.all_objects.update_or_create(
            post=post,
            user_id=2,
            defaults={"is_deleted": False},
        )
        Like.all_objects.update_or_create(
            post=second_post,
            user_id=1,
            defaults={"is_deleted": False},
        )
        Comment.all_objects.update_or_create(
            post=post,
            user_id=2,
            text="عالیه؛ فرم صحیح را حفظ کن و افزایش وزنه را تدریجی انجام بده.",
            defaults={
                "username": "user2",
                "is_deleted": False,
            },
        )

        article, _ = Content.all_objects.update_or_create(
            slug="warm-up-principles",
            defaults={
                "author_id": 2,
                "author_username": "user2",
                "title": "اصول گرم‌کردن پیش از تمرین",
                "content_type": ContentType.ARTICLE,
                "category": strength,
                "body": (
                    "پنج دقیقه فعالیت هوازی سبک، سپس حرکات پویا و دو ست آماده‌سازی "
                    "برای حرکت اصلی انجام دهید."
                ),
                "status": ContentStatus.PUBLISHED,
                "difficulty": DifficultyLevel.BEGINNER,
                "duration_minutes": 8,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        article.tags.set(Tag.objects.filter(slug__in=["beginner", "warm-up"]))
        nutrition_article, _ = Content.all_objects.update_or_create(
            slug="post-workout-meal",
            defaults={
                "author_id": 3,
                "author_username": "user3",
                "title": "وعده متعادل بعد از تمرین",
                "content_type": ContentType.ARTICLE,
                "category": nutrition,
                "body": "ترکیبی از پروتئین، کربوهیدرات پیچیده و مایعات انتخاب کنید.",
                "status": ContentStatus.PUBLISHED,
                "difficulty": DifficultyLevel.BEGINNER,
                "duration_minutes": 6,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        nutrition_article.tags.set(Tag.objects.filter(slug="healthy-nutrition"))
        ContentRating.all_objects.update_or_create(
            content=article,
            user_id=1,
            defaults={"score": 5, "is_deleted": False},
        )
        ContentView.all_objects.update_or_create(
            content=article,
            user_id=1,
            defaults={"view_count": 3, "is_deleted": False},
        )
        ContentView.all_objects.update_or_create(
            content=nutrition_article,
            user_id=1,
            defaults={"view_count": 1, "is_deleted": False},
        )

        course, _ = Course.all_objects.update_or_create(
            slug="bodybuilding-starter",
            defaults={
                "author_id": 2,
                "author_username": "user2",
                "title": "دوره رایگان شروع بدنسازی",
                "description": "مسیر شش‌درسـی برای شروع ایمن و اصولی بدنسازی.",
                "category": strength,
                "difficulty": DifficultyLevel.BEGINNER,
                "duration_minutes": 120,
                "is_free": True,
                "price": 0,
                "status": CourseStatus.PUBLISHED,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        course.tags.set(Tag.objects.filter(slug__in=["beginner", "bodybuilding"]))
        lesson_data = [
            (1, "معرفی مسیر تمرین", 15, article),
            (2, "اصول گرم‌کردن", 20, article),
            (3, "حرکت‌های پایه", 35, None),
            (4, "برنامه هفته اول", 50, None),
        ]
        lessons = []
        for order, title, duration, content in lesson_data:
            lesson, _ = Lesson.all_objects.update_or_create(
                course=course,
                order=order,
                defaults={
                    "title": title,
                    "duration_minutes": duration,
                    "content": content,
                    "body": f"محتوای درس {title}",
                    "is_preview": order == 1,
                    "is_deleted": False,
                },
            )
            lessons.append(lesson)

        enrollment, _ = Enrollment.all_objects.update_or_create(
            user_id=1,
            course=course,
            defaults={
                "status": EnrollmentStatus.IN_PROGRESS,
                "progress_percent": 25,
                "current_lesson": lessons[1],
                "is_deleted": False,
            },
        )
        for index, lesson in enumerate(lessons):
            LessonProgress.all_objects.update_or_create(
                enrollment=enrollment,
                lesson=lesson,
                defaults={
                    "is_completed": index == 0,
                    "watched_seconds": lesson.duration_minutes * 60 if index == 0 else 0,
                    "completed_at": timezone.now() if index == 0 else None,
                    "is_deleted": False,
                },
            )

        paid_course, _ = Course.all_objects.update_or_create(
            slug="advanced-strength-blueprint",
            defaults={
                "author_id": 2,
                "author_username": "user2",
                "title": "نقشه راه قدرت و عضله‌سازی",
                "description": (
                    "دوره کاربردی طراحی برنامه، پیشرفت وزنه و ریکاوری برای "
                    "ورزشکارانی که می‌خواهند اصولی‌تر تمرین کنند."
                ),
                "category": strength,
                "difficulty": DifficultyLevel.INTERMEDIATE,
                "duration_minutes": 165,
                "is_free": False,
                "price": 890000,
                "status": CourseStatus.PUBLISHED,
                "published_at": timezone.now(),
                "is_deleted": False,
            },
        )
        paid_course.tags.set(Tag.objects.filter(slug__in=["bodybuilding"]))
        paid_lesson_data = [
            (
                1,
                "ارزیابی سطح و تعیین هدف",
                25,
                (
                    "قبل از انتخاب برنامه، رکوردهای فعلی، سابقه آسیب، تعداد "
                    "جلسه‌های قابل انجام و هدف دوازده‌هفته‌ای خود را ثبت کنید.\n\n"
                    "تمرین عملی: یک هدف قابل اندازه‌گیری برای حرکت اسکوات، پرس "
                    "سینه یا ددلیفت بنویسید."
                ),
                True,
            ),
            (
                2,
                "طراحی حجم و شدت تمرین",
                40,
                (
                    "حجم تمرین از حاصل ست‌های مؤثر در هفته به دست می‌آید. "
                    "برای هر گروه عضلانی با حجم قابل بازیابی شروع کنید و تنها "
                    "زمانی آن را افزایش دهید که کیفیت اجرا و ریکاوری حفظ شده باشد."
                ),
                False,
            ),
            (
                3,
                "اصل اضافه‌بار تدریجی",
                45,
                (
                    "هر هفته فقط یکی از متغیرهای وزن، تکرار، ست یا کیفیت اجرا "
                    "را افزایش دهید. ثبت دقیق جلسه‌ها جلوی تصمیم‌های هیجانی را می‌گیرد."
                ),
                False,
            ),
            (
                4,
                "ریکاوری و هفته کاهش فشار",
                30,
                (
                    "خواب، تغذیه و مدیریت خستگی بخشی از برنامه‌اند. نشانه‌های "
                    "افت عملکرد را بشناسید و هر چهار تا شش هفته یک deload هدفمند داشته باشید."
                ),
                False,
            ),
            (
                5,
                "ساخت برنامه دوازده‌هفته‌ای",
                25,
                (
                    "اکنون سه بلوک چهارهفته‌ای بسازید: تثبیت تکنیک، افزایش حجم "
                    "و افزایش شدت. پایان هر بلوک را با داده‌های واقعی ارزیابی کنید."
                ),
                False,
            ),
        ]
        for order, title, duration, body, preview in paid_lesson_data:
            Lesson.all_objects.update_or_create(
                course=paid_course,
                order=order,
                defaults={
                    "title": title,
                    "duration_minutes": duration,
                    "body": body,
                    "is_preview": preview,
                    "is_deleted": False,
                },
            )

        DirectMessage.all_objects.update_or_create(
            sender_id=2,
            recipient_id=1,
            body="سلام امیر! اگر درباره برنامه شروع بدنسازی سؤال داشتی همین‌جا بپرس.",
            defaults={
                "sender_username": "user2",
                "recipient_username": "user1",
                "is_read": False,
                "is_deleted": False,
            },
        )
        DirectMessage.all_objects.update_or_create(
            sender_id=1,
            recipient_id=2,
            body="ممنون سارا، برای هفته دوم چند ست اسکوات پیشنهاد می‌کنی؟",
            defaults={
                "sender_username": "user1",
                "recipient_username": "user2",
                "is_read": True,
                "read_at": timezone.now(),
                "is_deleted": False,
            },
        )

        TrainingPlan.all_objects.update_or_create(
            author_id=2,
            title="برنامه چهار هفته‌ای فول‌بادی",
            defaults={
                "author_username": "user2",
                "description": "سه جلسه در هفته با تمرکز بر حرکات پایه.",
                "weeks": 4,
                "exercises": [
                    {"day": 1, "name": "اسکوات", "sets": 3, "reps": 10},
                    {"day": 1, "name": "پرس سینه", "sets": 3, "reps": 8},
                ],
                "is_published": True,
                "is_deleted": False,
            },
        )
        DietPlan.all_objects.update_or_create(
            author_id=3,
            title="الگوی غذایی هفت‌روزه ورزشکار مبتدی",
            defaults={
                "author_username": "user3",
                "description": "نمونه آموزشی؛ جایگزین توصیه پزشکی شخصی نیست.",
                "days": 7,
                "meals": [
                    {"day": 1, "meal": "صبحانه", "items": ["جو دوسر", "ماست", "میوه"]},
                    {"day": 1, "meal": "ناهار", "items": ["برنج", "مرغ", "سبزیجات"]},
                ],
                "is_published": True,
                "is_deleted": False,
            },
        )

        self.stdout.write(self.style.SUCCESS("Team 8 demo data is ready."))
