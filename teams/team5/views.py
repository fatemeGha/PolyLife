from django.shortcuts import render
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from django.utils import timezone

import json
import requests

from .models import (
    Exercise,
    WorkoutProgram,
    UserPreference,
    Favorite,
    WorkoutHistory,
)

from .serializers import (
    ExerciseSerializer,
    WorkoutProgramSerializer,
    UserPreferenceSerializer,
    FavoriteSerializer,
    WorkoutHistorySerializer,
)


def get_authenticated_user(request):
    user_id = request.headers.get("X-User-Id")
    username = request.headers.get("X-User-Username")

    if not user_id or not username:
        raise AuthenticationFailed("Authentication headers are missing.")

    return int(user_id), username


@api_view(["GET"])
def whoami(request):
    user_id, username = get_authenticated_user(request)
    return Response({
        "team": "team5",
        "user_id": user_id,
        "username": username,
    })


class ExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = ExerciseSerializer
    queryset = Exercise.objects.all()

    def get_queryset(self):
        qs = Exercise.objects.all()
        muscle = self.request.query_params.get("muscle")
        difficulty = self.request.query_params.get("difficulty")
        equipment = self.request.query_params.get("equipment")
        search = self.request.query_params.get("search")

        if muscle:
            qs = qs.filter(target_muscle__icontains=muscle)
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        if equipment:
            qs = qs.filter(equipment__icontains=equipment)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs.order_by("id")

    @action(detail=False, methods=["get"])
    def muscles(self, request):
        muscles = Exercise.objects.values_list("target_muscle", flat=True).distinct()
        return Response(sorted(muscles))

    @action(detail=False, methods=["get"])
    def equipments(self, request):
        equipments = Exercise.objects.values_list("equipment", flat=True).distinct()
        return Response(sorted(equipments))

    @action(detail=False, methods=["get"])
    def difficulties(self, request):
        levels = Exercise.objects.values_list("difficulty", flat=True).distinct()
        return Response(sorted(levels))


class WorkoutProgramViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutProgramSerializer
    queryset = WorkoutProgram.objects.all()

    def get_queryset(self):
        qs = WorkoutProgram.objects.all()
        difficulty = self.request.query_params.get("difficulty")
        search = self.request.query_params.get("search")

        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs.order_by("id")

    @action(detail=False, methods=["get"])
    def recommended(self, request):
        uid, _ = get_authenticated_user(request)
        preference = UserPreference.objects.filter(user_id=uid).first()
        if preference is None:
            return Response([])
        queryset = WorkoutProgram.objects.filter(difficulty__iexact=preference.level)
        serializer = WorkoutProgramSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def difficulties(self, request):
        levels = WorkoutProgram.objects.values_list("difficulty", flat=True).distinct()
        return Response(sorted(levels))


class UserPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferenceSerializer

    def get_queryset(self):
        user_id, _ = get_authenticated_user(self.request)
        return UserPreference.objects.filter(user_id=user_id)

    def perform_create(self, serializer):
        user_id, _ = get_authenticated_user(self.request)
        obj, _created = UserPreference.objects.update_or_create(
            user_id=user_id,
            defaults={
                "goal": serializer.validated_data["goal"],
                "level": serializer.validated_data["level"],
                "equipment": serializer.validated_data["equipment"],
            },
        )
        serializer.instance = obj

    def perform_update(self, serializer):
        user_id, _ = get_authenticated_user(self.request)
        serializer.save(user_id=user_id)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        user_id, _ = get_authenticated_user(self.request)
        return Favorite.objects.filter(user_id=user_id).order_by("-id")

    def perform_create(self, serializer):
        user_id, _ = get_authenticated_user(self.request)
        workout = serializer.validated_data["workout"]
        if Favorite.objects.filter(user_id=user_id, workout=workout).exists():
            raise ValidationError({"detail": "این برنامه قبلاً به علاقه‌مندی‌ها اضافه شده است."})
        serializer.save(user_id=user_id)


class WorkoutHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutHistorySerializer

    def get_queryset(self):
        user_id, _ = get_authenticated_user(self.request)
        return WorkoutHistory.objects.filter(user_id=user_id).order_by("-id")

    def perform_create(self, serializer):
        user_id, _ = get_authenticated_user(self.request)
        workout = serializer.validated_data["workout"]
        if WorkoutHistory.objects.filter(user_id=user_id, workout=workout).exists():
            raise ValidationError({"detail": "این برنامه قبلاً شروع شده است."})
        serializer.save(user_id=user_id)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        history = self.get_object()
        if history.completed:
            return Response({"detail": "این تمرین قبلاً پایان یافته است."})
        history.completed = True
        history.completed_at = timezone.now()
        history.save()
        return Response(WorkoutHistorySerializer(history).data)


class ReportViewSet(viewsets.ViewSet):
    @action(detail=False)
    def summary(self, request):
        return Response({
            "total_exercises": Exercise.objects.count(),
            "total_programs": WorkoutProgram.objects.count(),
            "total_histories": WorkoutHistory.objects.count(),
            "total_favorites": Favorite.objects.count(),
        })

    @action(detail=False)
    def users(self, request):
        active = (
            WorkoutHistory.objects.values("user_id").annotate(count=Count("id")).count()
        )
        return Response({"active_users": active})

    @action(detail=False, methods=["get"])
    def workouts(self, request):
        data = (
            WorkoutHistory.objects.values("workout", "workout__title")
            .annotate(times=Count("id"))
            .order_by("-times")
        )
        return Response(data)

    @action(detail=False)
    def activity(self, request):
        return Response({
            "completed_workouts": WorkoutHistory.objects.count(),
            "favorite_workouts": Favorite.objects.count(),
            "registered_preferences": UserPreference.objects.count(),
        })

    @action(detail=False)
    def dashboard(self, request):
        active_users = WorkoutHistory.objects.values("user_id").distinct().count()
        popular = (
            WorkoutHistory.objects.values("workout").annotate(times=Count("id")).order_by("-times").first()
        )
        return Response({
            "active_users": active_users,
            "total_exercises": Exercise.objects.count(),
            "total_programs": WorkoutProgram.objects.count(),
            "total_histories": WorkoutHistory.objects.count(),
            "total_favorites": Favorite.objects.count(),
            "most_used_program": popular,
        })


def index(request):
    return render(request, "team5/dashboard.html")


def login_page(request):
    return render(request, "team5/login.html")


@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method Not Allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode())
    except Exception:
        payload = {}

    try:
        response = requests.post("http://core:8000/api/login", json=payload, timeout=10)
    except requests.RequestException:
        return JsonResponse({"success": False, "message": "Core service unavailable"}, status=503)

    return JsonResponse(response.json(), status=response.status_code)


def exercise_page(request):
    return render(request, "team5/exercises.html")


def exercise_detail_page(request, pk):
    return render(request, "team5/exercise_detail.html", {"exercise_id": pk})


def workout_page(request):
    return render(request, "team5/workouts.html")


def workout_detail_page(request, pk):
    return render(request, "team5/workout_detail.html", {"program_id": pk})


def preference_page(request):
    return render(request, "team5/preferences.html")


def favorite_page(request):
    return render(request, "team5/favorites.html")


def history_page(request):
    return render(request, "team5/history.html")


def report_page(request):
    return render(request, "team5/reports.html")
