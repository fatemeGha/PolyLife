"""REST API and SPA entry points for Team 8."""

import mimetypes
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Subquery
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    CartItem,
    Category,
    Comment,
    Content,
    ContentRating,
    ContentStatus,
    ContentView,
    Course,
    CourseStatus,
    DietPlan,
    DirectMessage,
    Enrollment,
    EnrollmentStatus,
    Follow,
    Lesson,
    Like,
    Post,
    PostReport,
    PostStatus,
    Purchase,
    PurchaseStatus,
    Tag,
    TrainingPlan,
    UserProfile,
    UserRole,
)
from .permissions import IsCreatorRole, IsOwnerOrReadOnly, can_create, role_for
from .serializers import (
    ActivityItemSerializer,
    CartItemCreateSerializer,
    CartItemSerializer,
    CategorySerializer,
    CommentCreateSerializer,
    CommentSerializer,
    ContentRatingSerializer,
    ContentReadSerializer,
    ContentWriteSerializer,
    CourseReadSerializer,
    CourseWriteSerializer,
    DietPlanSerializer,
    DirectMessageCreateSerializer,
    DirectMessageSerializer,
    EnrollmentSerializer,
    HealthSerializer,
    LessonProgressUpdateSerializer,
    LessonAccessSerializer,
    LessonSerializer,
    PostReadSerializer,
    PostReportSerializer,
    PostWriteSerializer,
    PurchaseSerializer,
    TagSerializer,
    TrainingPlanSerializer,
    UserProfileSerializer,
)
from .services import (
    create_outbox_event,
    enroll_user,
    ensure_profile,
    feed_for,
    invalidate_author_audience,
    invalidate_user_feed,
    unique_slug,
    update_lesson_progress,
)


def _is_admin(user):
    return role_for(user) == UserRole.ADMIN


def _assert_owner_or_admin(user, obj):
    owner_id = getattr(obj, "author_id", getattr(obj, "user_id", None))
    if owner_id != user.id and not _is_admin(user):
        raise PermissionDenied("فقط مالک این منبع می‌تواند آن را تغییر دهد.")


def _filter_category(queryset, value):
    """Accept either a category slug or UUID without failing on malformed UUIDs."""
    condition = Q(category__slug=value)
    try:
        condition |= Q(category__id=uuid.UUID(value))
    except (ValueError, AttributeError):
        pass
    return queryset.filter(condition)


@extend_schema(tags=["Identity"], responses=HealthSerializer)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "polylife-team8",
            "version": "1.0.0",
        }
    )


def spa(request):
    """Serve the independently-built React app with client-side routing."""
    index_file = settings.FRONTEND_DIST / "index.html"
    if index_file.exists():
        response = HttpResponse(
            index_file.read_bytes(),
            content_type="text/html; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        return response
    return HttpResponse(
        "<main dir='rtl'><h1>PolyLife — میکروسرویس ۳</h1>"
        "<p>API فعال است؛ برای رابط کاربری پوشه frontend را build کنید.</p></main>",
        content_type="text/html; charset=utf-8",
    )


def spa_asset(request, path):
    """Serve immutable Vite assets without exposing arbitrary filesystem paths."""
    frontend_root = settings.FRONTEND_DIST.resolve()
    candidate = (frontend_root / "assets" / path).resolve()
    if not candidate.is_relative_to(frontend_root / "assets") or not candidate.is_file():
        raise Http404
    content_type, encoding = mimetypes.guess_type(candidate.name)
    response = FileResponse(
        candidate.open("rb"),
        content_type=content_type or "application/octet-stream",
    )
    if encoding:
        response["Content-Encoding"] = encoding
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@extend_schema(tags=["Identity"], responses=UserProfileSerializer)
@api_view(["GET"])
def whoami(request):
    profile, _ = ensure_profile(request.user)
    return Response(
        {
            "team": "team8",
            "user_id": request.user.id,
            "username": request.user.username,
            "profile": UserProfileSerializer(
                profile,
                context={"request": request},
            ).data,
        }
    )


def _activity_profile(user_id, request, username=""):
    profile = UserProfile.objects.filter(user_id=user_id).first()
    if profile:
        return UserProfileSerializer(profile, context={"request": request}).data
    return {
        "user_id": user_id,
        "username": username or f"user{user_id}",
        "display_name": username or f"user{user_id}",
        "avatar_url": None,
    }


@extend_schema(tags=["Activity"], responses=ActivityItemSerializer(many=True))
@api_view(["GET"])
def activity_feed(request):
    """Return real, openable activity items for the current user."""
    scope = request.query_params.get("scope", "me")
    user_id = request.user.id
    items = []

    def add(kind, obj, title, description, target_page, target_id=None, actor=None, unread=False):
        items.append(
            {
                "id": f"{kind}-{obj.id}",
                "type": kind,
                "title": title,
                "description": description,
                "created_at": obj.created_at,
                "target_page": target_page,
                "target_id": str(target_id) if target_id is not None else None,
                "actor": actor,
                "unread": unread,
            }
        )

    inbound_only = scope == "notifications"
    for relationship in Follow.objects.filter(following_id=user_id).order_by("-created_at")[:20]:
        actor = _activity_profile(relationship.follower_id, request)
        add(
            "follow",
            relationship,
            "دنبال‌کننده جدید",
            f"{actor['display_name'] or actor['username']} شما را دنبال کرد.",
            "member",
            relationship.follower_id,
            actor,
            True,
        )

    for like in (
        Like.objects.filter(post__author_id=user_id)
        .exclude(user_id=user_id)
        .select_related("post")
        .order_by("-created_at")[:20]
    ):
        actor = _activity_profile(like.user_id, request)
        add(
            "like",
            like,
            "پسند تازه",
            f"{actor['display_name'] or actor['username']} پست «{like.post.body[:55]}» را پسندید.",
            "feed",
            like.post_id,
            actor,
            True,
        )

    for comment in (
        Comment.objects.filter(post__author_id=user_id)
        .exclude(user_id=user_id)
        .select_related("post")
        .order_by("-created_at")[:20]
    ):
        actor = _activity_profile(comment.user_id, request, comment.username)
        add(
            "comment",
            comment,
            "دیدگاه جدید",
            f"{actor['display_name'] or actor['username']}: {comment.text[:90]}",
            "feed",
            comment.post_id,
            actor,
            True,
        )

    for message in DirectMessage.objects.filter(recipient_id=user_id).order_by("-created_at")[:20]:
        actor = _activity_profile(message.sender_id, request, message.sender_username)
        add(
            "message",
            message,
            "پیام مستقیم",
            f"{actor['display_name'] or actor['username']}: {message.body[:90]}",
            "messages",
            message.sender_id,
            actor,
            not message.is_read,
        )

    if not inbound_only:
        for post in Post.objects.filter(author_id=user_id).order_by("-created_at")[:20]:
            add(
                "post",
                post,
                "انتشار در جامعه",
                post.body[:120],
                "feed",
                post.id,
            )
        for enrollment in (
            Enrollment.objects.filter(user_id=user_id)
            .select_related("course")
            .order_by("-updated_at")[:20]
        ):
            add(
                "course",
                enrollment,
                "فعالیت آموزشی",
                f"{enrollment.course.title} — {enrollment.progress_percent}٪ پیشرفت",
                "courses",
                enrollment.course_id,
            )
        for purchase in (
            Purchase.objects.filter(user_id=user_id)
            .select_related("course")
            .order_by("-paid_at")[:20]
        ):
            add(
                "purchase",
                purchase,
                "خرید موفق",
                f"{purchase.course.title} با شماره پیگیری {purchase.reference}",
                "transactions",
                purchase.id,
            )

    items.sort(key=lambda item: item["created_at"], reverse=True)
    return Response(items[:60])


class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "user_id"

    def get_queryset(self):
        queryset = UserProfile.objects.all().order_by("-is_verified", "display_name")
        query = self.request.query_params.get("q", "").strip()
        role = self.request.query_params.get("role", "").strip()
        specialization = self.request.query_params.get("specialization", "").strip()
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(display_name__icontains=query)
                | Q(specialization__icontains=query)
            )
        if role:
            queryset = queryset.filter(role=role)
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)
        return queryset

    @extend_schema(tags=["Identity"], responses=UserProfileSerializer)
    @action(detail=False, methods=["get", "patch", "put"], url_path="me")
    def me(self, request):
        profile, _ = ensure_profile(request.user)
        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"])
    def follow(self, request, user_id=None):
        target = self.get_object()
        if target.user_id == request.user.id:
            raise ValidationError({"user_id": "کاربر نمی‌تواند خودش را دنبال کند."})

        relationship = Follow.all_objects.filter(
            follower_id=request.user.id,
            following_id=target.user_id,
        ).first()
        if request.method == "POST":
            if relationship:
                relationship.is_deleted = False
                relationship.save(update_fields=["is_deleted", "updated_at"])
            else:
                relationship = Follow.objects.create(
                    follower_id=request.user.id,
                    following_id=target.user_id,
                )
            invalidate_user_feed(request.user.id)
            return Response({"following": True}, status=status.HTTP_200_OK)

        if relationship and not relationship.is_deleted:
            relationship.delete()
        invalidate_user_feed(request.user.id)
        return Response({"following": False}, status=status.HTTP_200_OK)

    def _relationship_profiles(self, request, queryset, field):
        user_ids = queryset.values_list(field, flat=True)
        profiles = UserProfile.objects.filter(user_id__in=user_ids).order_by(
            "-is_verified",
            "display_name",
        )
        page = self.paginate_queryset(profiles)
        items = page if page is not None else profiles
        serializer = self.get_serializer(items, many=True)
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=True, methods=["get"])
    def followers(self, request, user_id=None):
        target = self.get_object()
        return self._relationship_profiles(
            request,
            Follow.objects.filter(following_id=target.user_id),
            "follower_id",
        )

    @action(detail=True, methods=["get"])
    def following(self, request, user_id=None):
        target = self.get_object()
        return self._relationship_profiles(
            request,
            Follow.objects.filter(follower_id=target.user_id),
            "following_id",
        )


class DirectMessageViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DirectMessageSerializer
    queryset = DirectMessage.objects.none()

    def list(self, request):
        messages = (
            DirectMessage.objects.filter(
                Q(sender_id=request.user.id) | Q(recipient_id=request.user.id)
            )
            .order_by("-created_at")
        )
        threads = []
        seen = set()
        for message in messages:
            counterpart_id = (
                message.recipient_id
                if message.sender_id == request.user.id
                else message.sender_id
            )
            if counterpart_id in seen:
                continue
            seen.add(counterpart_id)
            counterpart_username = (
                message.recipient_username
                if message.sender_id == request.user.id
                else message.sender_username
            )
            threads.append(
                {
                    "profile": _activity_profile(
                        counterpart_id,
                        request,
                        counterpart_username,
                    ),
                    "last_message": DirectMessageSerializer(
                        message,
                        context={"request": request},
                    ).data,
                    "unread_count": DirectMessage.objects.filter(
                        sender_id=counterpart_id,
                        recipient_id=request.user.id,
                        is_read=False,
                    ).count(),
                }
            )
            if len(threads) >= 50:
                break
        return Response(threads)

    @action(
        detail=False,
        methods=["get", "post"],
        url_path=r"with/(?P<user_id>\d+)",
    )
    def thread(self, request, user_id=None):
        target = UserProfile.objects.filter(user_id=user_id).first()
        if not target:
            raise NotFound("کاربر موردنظر پیدا نشد.")
        if target.user_id == request.user.id:
            raise ValidationError("ارسال پیام به خودتان امکان‌پذیر نیست.")

        if request.method == "POST":
            serializer = DirectMessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            message = DirectMessage.objects.create(
                sender_id=request.user.id,
                sender_username=request.user.username,
                recipient_id=target.user_id,
                recipient_username=target.username,
                body=serializer.validated_data["body"],
            )
            return Response(
                DirectMessageSerializer(
                    message,
                    context={"request": request},
                ).data,
                status=status.HTTP_201_CREATED,
            )

        DirectMessage.objects.filter(
            sender_id=target.user_id,
            recipient_id=request.user.id,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now(), updated_at=timezone.now())
        messages = DirectMessage.objects.filter(
            Q(sender_id=request.user.id, recipient_id=target.user_id)
            | Q(sender_id=target.user_id, recipient_id=request.user.id)
        ).order_by("-created_at")[:100]
        return Response(
            {
                "profile": UserProfileSerializer(
                    target,
                    context={"request": request},
                ).data,
                "messages": DirectMessageSerializer(
                    list(reversed(messages)),
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PostWriteSerializer
        return PostReadSerializer

    def get_permissions(self):
        if self.action in {
            "feed",
            "explore",
            "mine",
            "like",
            "comments",
            "report",
        }:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Post.objects.select_related("workout")
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
                        user_id=self.request.user.id,
                        is_deleted=False,
                    )
                ),
            )
            .filter(
                Q(status=PostStatus.PUBLISHED) | Q(author_id=self.request.user.id)
            )
        )
        query = self.request.query_params.get("q", "").strip()
        post_type = self.request.query_params.get("type", "").strip()
        author_id = self.request.query_params.get("author_id", "").strip()
        if query:
            queryset = queryset.filter(
                Q(body__icontains=query)
                | Q(workout__exercise_type__icontains=query)
            )
        if post_type:
            queryset = queryset.filter(post_type=post_type)
        if author_id.isdigit():
            queryset = queryset.filter(author_id=int(author_id))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        return Response(
            PostReadSerializer(post, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        return Response(PostReadSerializer(post, context=self.get_serializer_context()).data)

    def perform_destroy(self, instance):
        _assert_owner_or_admin(self.request.user, instance)
        instance.delete()
        invalidate_author_audience(instance.author_id)

    @action(detail=False, methods=["get"])
    def feed(self, request):
        posts = feed_for(request.user.id)
        page = self.paginate_queryset(posts)
        items = page if page is not None else posts
        serializer = PostReadSerializer(
            items,
            many=True,
            context=self.get_serializer_context(),
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=False, methods=["get"])
    def explore(self, request):
        queryset = self.get_queryset().filter(status=PostStatus.PUBLISHED).order_by(
            "-like_count_value",
            "-published_at",
        )
        page = self.paginate_queryset(queryset)
        items = page if page is not None else queryset
        serializer = PostReadSerializer(
            items,
            many=True,
            context=self.get_serializer_context(),
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.get_queryset().filter(author_id=request.user.id)
        page = self.paginate_queryset(queryset)
        items = page if page is not None else queryset
        serializer = PostReadSerializer(
            items,
            many=True,
            context=self.get_serializer_context(),
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=True, methods=["post", "delete"])
    def like(self, request, pk=None):
        post = self.get_object()
        like = Like.all_objects.filter(post=post, user_id=request.user.id).first()
        if request.method == "POST":
            if like:
                like.is_deleted = False
                like.save(update_fields=["is_deleted", "updated_at"])
            else:
                Like.objects.create(post=post, user_id=request.user.id)
            return Response(
                {"liked": True, "like_count": post.likes.filter(is_deleted=False).count()}
            )
        if like and not like.is_deleted:
            like.delete()
        return Response(
            {"liked": False, "like_count": post.likes.filter(is_deleted=False).count()}
        )

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == "GET":
            queryset = post.comments.filter(is_deleted=False, parent__isnull=True)
            serializer = CommentSerializer(
                queryset,
                many=True,
                context=self.get_serializer_context(),
            )
            return Response(serializer.data)

        input_serializer = CommentCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        parent = None
        parent_id = input_serializer.validated_data.get("parent_id")
        if parent_id:
            parent = Comment.objects.filter(id=parent_id, post=post).first()
            if not parent:
                raise ValidationError({"parent_id": "کامنت والد در این پست یافت نشد."})
        comment = Comment.objects.create(
            post=post,
            user_id=request.user.id,
            username=request.user.username,
            parent=parent,
            text=input_serializer.validated_data["text"],
        )
        return Response(
            CommentSerializer(comment, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        post = self.get_object()
        serializer = PostReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = PostReport.all_objects.filter(
            post=post,
            reporter_id=request.user.id,
        ).first()
        if report and not report.is_deleted:
            raise ValidationError("این پست قبلاً توسط شما گزارش شده است.")
        if report:
            report.reason = serializer.validated_data["reason"]
            report.is_deleted = False
            report.save(update_fields=["reason", "is_deleted", "updated_at"])
        else:
            report = PostReport.objects.create(
                post=post,
                reporter_id=request.user.id,
                reason=serializer.validated_data["reason"],
            )
        if post.reports.filter(status="open", is_deleted=False).count() >= 3:
            post.status = PostStatus.REPORTED
            post.save(update_fields=["status", "updated_at"])
        return Response(
            PostReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.select_related("parent").all()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsCreatorRole()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(slug=unique_slug(Category, serializer.validated_data["name"]))

    def perform_update(self, serializer):
        name = serializer.validated_data.get("name", serializer.instance.name)
        serializer.save(slug=unique_slug(Category, name, instance=serializer.instance))

    def perform_destroy(self, instance):
        if (
            instance.children.exists()
            or instance.contents.exists()
            or instance.courses.exists()
        ):
            raise ValidationError(
                "دسته‌ای که زیر‌دسته، محتوا یا دورهٔ فعال دارد قابل حذف نیست."
            )
        instance.delete()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tag.objects.all()


class ContentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ContentWriteSerializer
        if self.action == "rate":
            return ContentRatingSerializer
        return ContentReadSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsCreatorRole()]
        if self.action == "rate":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Content.objects.select_related("category")
            .prefetch_related("tags")
            .annotate(
                average_rating_value=Avg(
                    "ratings__score",
                    filter=Q(ratings__is_deleted=False),
                ),
                rating_count_value=Count(
                    "ratings",
                    filter=Q(ratings__is_deleted=False),
                    distinct=True,
                ),
                my_rating_value=Subquery(
                    ContentRating.objects.filter(
                        content_id=OuterRef("pk"),
                        user_id=self.request.user.id,
                    ).values("score")[:1]
                ),
            )
            .filter(
                Q(status=ContentStatus.PUBLISHED) | Q(author_id=self.request.user.id)
            )
        )
        query = self.request.query_params.get("q", "").strip()
        content_type = self.request.query_params.get("type", "").strip()
        category = self.request.query_params.get("category", "").strip()
        difficulty = self.request.query_params.get("difficulty", "").strip()
        tag = self.request.query_params.get("tag", "").strip()
        mine = self.request.query_params.get("mine", "").lower() == "true"
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(body__icontains=query)
                | Q(tags__name__icontains=query)
            )
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if category:
            queryset = _filter_category(queryset, category)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if mine:
            queryset = queryset.filter(author_id=self.request.user.id)
        return queryset.distinct().order_by("-published_at", "-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.save()
        return Response(
            ContentReadSerializer(content, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        content = self.get_object()
        history = ContentView.all_objects.filter(
            content=content,
            user_id=request.user.id,
        ).first()
        if history:
            history.view_count += 1
            history.is_deleted = False
            history.save(update_fields=["view_count", "is_deleted", "updated_at"])
        else:
            ContentView.objects.create(content=content, user_id=request.user.id)
        return Response(
            ContentReadSerializer(
                content,
                context=self.get_serializer_context(),
            ).data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _assert_owner_or_admin(request.user, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        content = serializer.save()
        return Response(
            ContentReadSerializer(content, context=self.get_serializer_context()).data
        )

    def perform_destroy(self, instance):
        _assert_owner_or_admin(self.request.user, instance)
        Lesson.objects.filter(content=instance).update(content=None)
        instance.delete()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        content = self.get_object()
        _assert_owner_or_admin(request.user, content)
        if content.content_type == "video" and not content.media:
            raise ValidationError({"media": "فایل ویدیویی برای انتشار لازم است."})
        content.status = ContentStatus.PUBLISHED
        content.published_at = content.published_at or timezone.now()
        content.save(update_fields=["status", "published_at", "updated_at"])
        create_outbox_event(
            "content.published",
            content,
            {"author_id": content.author_id, "content_type": content.content_type},
        )
        return Response(
            ContentReadSerializer(content, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        content = self.get_object()
        _assert_owner_or_admin(request.user, content)
        content.status = ContentStatus.ARCHIVED
        content.save(update_fields=["status", "updated_at"])
        return Response(
            ContentReadSerializer(content, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["put"])
    def rate(self, request, pk=None):
        content = self.get_object()
        serializer = ContentRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = ContentRating.all_objects.filter(
            content=content,
            user_id=request.user.id,
        ).first()
        if rating:
            rating.score = serializer.validated_data["score"]
            rating.is_deleted = False
            rating.save()
        else:
            rating = ContentRating.objects.create(
                content=content,
                user_id=request.user.id,
                score=serializer.validated_data["score"],
            )
        return Response(ContentRatingSerializer(rating).data)

    @action(detail=True, methods=["get"])
    def recommendations(self, request, pk=None):
        content = self.get_object()
        recently_viewed = list(
            ContentView.objects.filter(user_id=request.user.id)
            .order_by("-updated_at")
            .values_list("content_id", flat=True)[:20]
        )
        history = Content.objects.filter(pk__in=recently_viewed)
        category_ids = list(history.values_list("category_id", flat=True).distinct())
        tag_ids = list(history.values_list("tags__id", flat=True).distinct())

        queryset = Content.objects.filter(status=ContentStatus.PUBLISHED)
        if category_ids or tag_ids:
            queryset = queryset.filter(
                Q(category_id__in=category_ids) | Q(tags__id__in=tag_ids)
            ).exclude(pk__in=recently_viewed)
        else:
            queryset = queryset.filter(category=content.category).exclude(pk=content.pk)
        queryset = queryset.distinct().order_by("-published_at")[:6]
        return Response(
            ContentReadSerializer(
                queryset,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return CourseWriteSerializer
        return CourseReadSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsCreatorRole()]
        if self.action == "enroll":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Course.objects.select_related("category")
            .prefetch_related("tags", "lessons", "lessons__content")
            .annotate(
                lesson_count=Count(
                    "lessons",
                    filter=Q(lessons__is_deleted=False),
                ),
                enrollment_id_value=Subquery(
                    Enrollment.objects.filter(
                        course_id=OuterRef("pk"),
                        user_id=self.request.user.id,
                    ).values("id")[:1]
                ),
            )
            .filter(Q(status=CourseStatus.PUBLISHED) | Q(author_id=self.request.user.id))
        )
        query = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()
        difficulty = self.request.query_params.get("difficulty", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__name__icontains=query)
            )
        if category:
            queryset = _filter_category(queryset, category)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        return queryset.distinct().order_by("-published_at", "-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        return Response(
            CourseReadSerializer(course, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _assert_owner_or_admin(request.user, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        return Response(
            CourseReadSerializer(course, context=self.get_serializer_context()).data
        )

    def perform_destroy(self, instance):
        _assert_owner_or_admin(self.request.user, instance)
        if instance.enrollments.exists():
            raise ValidationError(
                "دوره‌ای که ثبت‌نام فعال دارد قابل حذف نیست؛ آن را بایگانی کنید."
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        course = self.get_object()
        try:
            enrollment, created = enroll_user(request.user, course)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(
            EnrollmentSerializer(
                enrollment,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        course = self.get_object()
        _assert_owner_or_admin(request.user, course)
        if not course.is_free and not course.price:
            raise ValidationError("برای دوره پولی باید قیمت بیشتر از صفر ثبت شود.")
        if not course.lessons.exists():
            raise ValidationError("دوره باید حداقل یک درس داشته باشد.")
        course.status = CourseStatus.PUBLISHED
        course.published_at = course.published_at or timezone.now()
        course.save(update_fields=["status", "published_at", "updated_at"])
        return Response(
            CourseReadSerializer(course, context=self.get_serializer_context()).data
        )


class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.none()

    def _queryset(self, request):
        return (
            CartItem.objects.filter(user_id=request.user.id)
            .select_related("course", "course__category")
            .order_by("created_at")
        )

    def list(self, request):
        items = self._queryset(request)
        return Response(
            CartItemSerializer(
                items,
                many=True,
                context={"request": request},
            ).data
        )

    def create(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = Course.objects.filter(
            id=serializer.validated_data["course_id"],
            status=CourseStatus.PUBLISHED,
        ).first()
        if not course:
            raise NotFound("دوره موردنظر پیدا نشد.")
        if course.is_free:
            raise ValidationError("دوره رایگان نیازی به سبد خرید ندارد.")
        if Purchase.objects.filter(
            user_id=request.user.id,
            course=course,
            status=PurchaseStatus.COMPLETED,
        ).exists():
            raise ValidationError("این دوره قبلاً خریداری شده است.")

        item = CartItem.all_objects.filter(
            user_id=request.user.id,
            course=course,
        ).first()
        created = item is None
        if item:
            item.is_deleted = False
            item.save(update_fields=["is_deleted", "updated_at"])
        else:
            item = CartItem.objects.create(user_id=request.user.id, course=course)
        return Response(
            CartItemSerializer(item, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        item = self._queryset(request).filter(pk=pk).first()
        if not item:
            raise NotFound("آیتم سبد خرید پیدا نشد.")
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        cart_items = list(
            self._queryset(request)
            .select_for_update()
        )
        if not cart_items:
            raise ValidationError("سبد خرید خالی است.")

        purchases = []
        for item in cart_items:
            course = item.course
            if course.status != CourseStatus.PUBLISHED or course.is_free:
                raise ValidationError(
                    f"دوره «{course.title}» در حال حاضر قابل خرید نیست."
                )
            purchase = Purchase.all_objects.filter(
                user_id=request.user.id,
                course=course,
            ).first()
            if purchase:
                purchase.amount = course.price
                purchase.status = PurchaseStatus.COMPLETED
                purchase.paid_at = timezone.now()
                purchase.is_deleted = False
                purchase.save()
            else:
                purchase = Purchase.objects.create(
                    user_id=request.user.id,
                    course=course,
                    amount=course.price,
                )
            enrollment, _ = enroll_user(request.user, course)
            purchases.append(purchase)
            item.delete()
            create_outbox_event(
                "course.purchased",
                purchase,
                {
                    "user_id": request.user.id,
                    "course_id": str(course.id),
                    "amount": purchase.amount,
                    "enrollment_id": str(enrollment.id),
                },
            )

        return Response(
            {
                "success": True,
                "message": "پرداخت شبیه‌سازی شد و دوره‌ها فعال شدند.",
                "purchases": PurchaseSerializer(
                    purchases,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class PurchaseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Purchase.objects.filter(user_id=self.request.user.id)
            .select_related("course", "course__category")
            .order_by("-paid_at")
        )


class LessonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return LessonAccessSerializer
        return LessonSerializer

    def get_queryset(self):
        return Lesson.objects.select_related("course", "content").filter(
            Q(course__status=CourseStatus.PUBLISHED)
            | Q(course__author_id=self.request.user.id)
        )

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        _assert_owner_or_admin(self.request.user, course)
        if not can_create(self.request.user):
            raise PermissionDenied("فقط مربی یا متخصص می‌تواند درس ایجاد کند.")
        serializer.save()

    def perform_update(self, serializer):
        _assert_owner_or_admin(self.request.user, serializer.instance.course)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_owner_or_admin(self.request.user, instance.course)
        instance.delete()


class EnrollmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Enrollment.objects.none()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Enrollment.objects.filter(user_id=self.request.user.id)
            .select_related("course", "course__category", "current_lesson")
            .prefetch_related("lesson_progress", "lesson_progress__lesson")
            .order_by("-created_at")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "lesson_id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
            )
        ],
        request=LessonProgressUpdateSerializer,
        responses=EnrollmentSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=r"lessons/(?P<lesson_id>[^/.]+)",
    )
    def lesson(self, request, pk=None, lesson_id=None):
        enrollment = self.get_object()
        lesson = Lesson.objects.filter(id=lesson_id, course=enrollment.course).first()
        if not lesson:
            raise NotFound("درس موردنظر در این دوره وجود ندارد.")
        serializer = LessonProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _, enrollment = update_lesson_progress(
                enrollment,
                lesson,
                serializer.validated_data["watched_seconds"],
                serializer.validated_data["is_completed"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(
            EnrollmentSerializer(
                enrollment,
                context=self.get_serializer_context(),
            ).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = EnrollmentStatus.CANCELLED
        enrollment.save(update_fields=["status", "updated_at"])
        return Response(
            EnrollmentSerializer(
                enrollment,
                context=self.get_serializer_context(),
            ).data
        )


class OwnedPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    model = None

    def get_queryset(self):
        queryset = self.model.objects.filter(
            Q(is_published=True) | Q(author_id=self.request.user.id)
        )
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        if not can_create(self.request.user):
            raise PermissionDenied("فقط مربی یا متخصص می‌تواند برنامه ایجاد کند.")
        serializer.save(
            author_id=self.request.user.id,
            author_username=self.request.user.username,
        )

    def perform_update(self, serializer):
        _assert_owner_or_admin(self.request.user, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_owner_or_admin(self.request.user, instance)
        instance.delete()


class TrainingPlanViewSet(OwnedPlanViewSet):
    model = TrainingPlan
    serializer_class = TrainingPlanSerializer


class DietPlanViewSet(OwnedPlanViewSet):
    model = DietPlan
    serializer_class = DietPlanSerializer

    def perform_create(self, serializer):
        profile = UserProfile.objects.filter(user_id=self.request.user.id).first()
        if not profile or not (
            profile.role == UserRole.ADMIN
            or (
                profile.role == UserRole.NUTRITION_SPECIALIST
                and profile.is_verified
            )
        ):
            raise PermissionDenied("فقط متخصص تغذیه می‌تواند برنامه رژیمی ایجاد کند.")
        serializer.save(
            author_id=self.request.user.id,
            author_username=self.request.user.username,
        )
