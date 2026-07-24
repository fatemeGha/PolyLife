"""Object and role-level permissions for Team 8 resources."""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import UserProfile, UserRole

CREATOR_ROLES = {
    UserRole.COACH,
    UserRole.SPORTS_DOCTOR,
    UserRole.NUTRITION_SPECIALIST,
    UserRole.ADMIN,
}


def role_for(user):
    return (
        UserProfile.objects.filter(user_id=user.id).values_list("role", flat=True).first()
        or UserRole.ATHLETE
    )


def can_create(user):
    profile = UserProfile.objects.filter(user_id=user.id).first()
    if not profile:
        return False
    return profile.role == UserRole.ADMIN or (
        profile.role in CREATOR_ROLES and profile.is_verified
    )


class IsCreatorRole(BasePermission):
    message = "فقط مربی یا متخصص تأییدشده می‌تواند این عملیات را انجام دهد."

    def has_permission(self, request, view):
        return request.user.is_authenticated and can_create(request.user)


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_id = getattr(obj, "author_id", getattr(obj, "user_id", None))
        return owner_id == request.user.id or role_for(request.user) == UserRole.ADMIN


class IsAdminRole(BasePermission):
    message = "این عملیات فقط برای مدیر محتوا مجاز است."

    def has_permission(self, request, view):
        return request.user.is_authenticated and role_for(request.user) == UserRole.ADMIN
