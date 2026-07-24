from django.db import transaction
from django.utils import timezone

from ..exceptions import (
    AlreadyMemberError,
    GroupFullError,
    GroupNotFoundError,
    HighRiskGroupError,
    MembershipNotFoundError,
)
from ..models import (
    GroupMembership,
    MembershipStatus,
    RiskLevel,
    TrainingGroup,
)
from .risk_service import analyze_group_risk


ACTIVE_MEMBERSHIP_STATUSES = {
    MembershipStatus.ACTIVE,
    MembershipStatus.PENDING,
}


def _get_existing_membership(
    *,
    user,
    group,
    for_update=False,
):
    queryset = GroupMembership.objects.filter(
        user_profile=user,
        group=group,
    )

    if for_update:
        queryset = queryset.select_for_update()

    return queryset.first()


def _get_active_member_count(group):
    return GroupMembership.objects.filter(
        group=group,
        status=MembershipStatus.ACTIVE,
    ).count()


def _lock_group(group):
    group_id = getattr(
        group,
        "pk",
        getattr(group, "id", None),
    )

    try:
        return (
            TrainingGroup.objects
            .select_for_update()
            .get(pk=group_id)
        )
    except TrainingGroup.DoesNotExist as exc:
        raise GroupNotFoundError() from exc


def _get_membership_for_update(
    *,
    user,
    membership_id,
):
    try:
        return (
            GroupMembership.objects
            .select_for_update()
            .select_related("group")
            .get(
                id=membership_id,
                user_profile=user,
            )
        )
    except GroupMembership.DoesNotExist as exc:
        raise MembershipNotFoundError() from exc


def get_user_memberships(*, user):
    return (
        GroupMembership.objects
        .filter(user_profile=user)
        .select_related("group")
        .order_by("-joined_at", "-id")
    )


def get_membership(
    *,
    user,
    membership_id,
):
    try:
        return (
            GroupMembership.objects
            .select_related("group")
            .get(
                id=membership_id,
                user_profile=user,
            )
        )
    except GroupMembership.DoesNotExist as exc:
        raise MembershipNotFoundError() from exc


def join_group(
    *,
    user,
    group,
):
    existing_membership = _get_existing_membership(
        user=user,
        group=group,
    )

    if (
        existing_membership
        and existing_membership.status
        in ACTIVE_MEMBERSHIP_STATUSES
    ):
        raise AlreadyMemberError()

    if (
        _get_active_member_count(group)
        >= group.max_members
    ):
        raise GroupFullError()

    risk = analyze_group_risk(
        user=user,
        group=group,
        persist=True,
    )

    if risk["level"] == RiskLevel.HIGH:
        raise HighRiskGroupError(
            details={
                "risk_score": risk["score"],
                "risk_level": risk["level"],
            }
        )

    with transaction.atomic():
        locked_group = _lock_group(group)

        existing_membership = (
            _get_existing_membership(
                user=user,
                group=locked_group,
                for_update=True,
            )
        )

        if (
            existing_membership
            and existing_membership.status
            in ACTIVE_MEMBERSHIP_STATUSES
        ):
            raise AlreadyMemberError()

        if (
            _get_active_member_count(locked_group)
            >= locked_group.max_members
        ):
            raise GroupFullError()

        if existing_membership:
            existing_membership.status = (
                MembershipStatus.ACTIVE
            )
            existing_membership.joined_at = (
                timezone.now()
            )
            existing_membership.save(
                update_fields=[
                    "status",
                    "joined_at",
                ]
            )

            membership = existing_membership

        else:
            membership = (
                GroupMembership.objects.create(
                    user_profile=user,
                    group=locked_group,
                    status=MembershipStatus.ACTIVE,
                )
            )

    return {
        "membership": membership,
        "risk": risk,
    }


def leave_group(
    *,
    user,
    membership_id,
):
    with transaction.atomic():
        membership = _get_membership_for_update(
            user=user,
            membership_id=membership_id,
        )

        if membership.status != MembershipStatus.LEFT:
            membership.status = MembershipStatus.LEFT
            membership.save(
                update_fields=["status"]
            )

    return membership
def get_group_members(*, group):
    return (
        GroupMembership.objects
        .filter(
            group=group,
            status=MembershipStatus.ACTIVE,
        )
        .select_related("user_profile")
        .order_by("joined_at", "id")
    )