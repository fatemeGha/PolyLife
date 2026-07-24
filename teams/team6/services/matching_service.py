from ..models import (
    DifficultyLevel,
    GroupMembership,
    MembershipStatus,
    RiskLevel,
    TrainingGroup,
)
from .risk_service import analyze_group_risk
from types import SimpleNamespace


FITNESS_DIFFICULTY_SCORES = {
    ("beginner", DifficultyLevel.EASY): 25,
    ("beginner", DifficultyLevel.MEDIUM): 15,
    ("beginner", DifficultyLevel.HARD): 0,
    ("intermediate", DifficultyLevel.EASY): 20,
    ("intermediate", DifficultyLevel.MEDIUM): 25,
    ("intermediate", DifficultyLevel.HARD): 15,
    ("advanced", DifficultyLevel.EASY): 15,
    ("advanced", DifficultyLevel.MEDIUM): 20,
    ("advanced", DifficultyLevel.HARD): 25,
}


def _normalize_text(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _normalize_list(values):
    if not values:
        return []

    normalized_values = []

    for value in values:
        normalized_value = _normalize_text(value)

        if normalized_value:
            normalized_values.append(normalized_value)

    return normalized_values


def _time_to_minutes(value):
    return (value.hour * 60) + value.minute


def _calculate_time_overlap_score(
    *,
    group_start_time,
    group_end_time,
    preferred_start_time,
    preferred_end_time,
):
    group_start = _time_to_minutes(group_start_time)
    group_end = _time_to_minutes(group_end_time)

    preferred_start = _time_to_minutes(
        preferred_start_time
    )
    preferred_end = _time_to_minutes(
        preferred_end_time
    )

    overlap_start = max(group_start, preferred_start)
    overlap_end = min(group_end, preferred_end)

    overlap_minutes = max(
        overlap_end - overlap_start,
        0,
    )

    group_duration = group_end - group_start

    if group_duration <= 0:
        return 0

    overlap_ratio = overlap_minutes / group_duration

    return round(overlap_ratio * 10)


def _calculate_day_score(
    *,
    group_days,
    user_days,
):
    normalized_group_days = set(
        _normalize_list(group_days)
    )
    normalized_user_days = set(
        _normalize_list(user_days)
    )

    if not normalized_group_days:
        return 0

    matching_days = (
        normalized_group_days
        & normalized_user_days
    )

    match_ratio = (
        len(matching_days)
        / len(normalized_group_days)
    )

    return round(match_ratio * 10)


def _calculate_equipment_score(
    *,
    required_equipment,
    user_equipment,
):
    normalized_required_equipment = set(
        _normalize_list(required_equipment)
    )

    normalized_user_equipment = set(
        _normalize_list(user_equipment)
    )

    if not normalized_required_equipment:
        return 10

    available_equipment = (
        normalized_required_equipment
        & normalized_user_equipment
    )

    match_ratio = (
        len(available_equipment)
        / len(normalized_required_equipment)
    )

    return round(match_ratio * 10)


def _calculate_match_score(
    *,
    group,
    goal_id,
    fitness_level,
    workout_type,
    available_days,
    preferred_start_time,
    preferred_end_time,
    equipment,
):
    score = 0

    group_goal_id = getattr(
        group,
        "goal_id",
        None,
    )

    if group_goal_id is None:
        group_goal = getattr(group, "goal", None)
        group_goal_id = getattr(group_goal, "id", None)

    if group_goal_id == goal_id:
        score += 30

    fitness_key = (
        _normalize_text(fitness_level),
        group.difficulty_level,
    )

    score += FITNESS_DIFFICULTY_SCORES.get(
        fitness_key,
        0,
    )

    score += _calculate_day_score(
        group_days=group.available_days,
        user_days=available_days,
    )

    score += _calculate_time_overlap_score(
        group_start_time=group.start_time,
        group_end_time=group.end_time,
        preferred_start_time=preferred_start_time,
        preferred_end_time=preferred_end_time,
    )

    if (
        _normalize_text(group.workout_type)
        == _normalize_text(workout_type)
    ):
        score += 15

    score += _calculate_equipment_score(
        required_equipment=group.equipment,
        user_equipment=equipment,
    )

    return min(max(int(score), 0), 100)


def _get_candidate_groups(goal_id):
    return list(
        TrainingGroup.objects
        .filter(goal_id=goal_id)
        .select_related("goal")
        .order_by("id")
    )


def _get_active_member_count(group):
    return GroupMembership.objects.filter(
        group=group,
        status=MembershipStatus.ACTIVE,
    ).count()


def recommend_groups(
    *,
    user,
    goal_id,
    fitness_level,
    workout_type,
    available_days,
    preferred_start_time,
    preferred_end_time,
    equipment=None,
    physical_limitations=None,
    minimum_score=40,
    limit=10,
):
    equipment = equipment or []
    physical_limitations = physical_limitations or []

    temporary_injuries = [
        SimpleNamespace(
            injury_type="Temporary physical limitation",
            body_part=item["body_part"],
            severity=item["severity"],
        )
        for item in physical_limitations
    ]

    groups = _get_candidate_groups(goal_id)
    recommendations = []

    for group in groups:
        member_count = _get_active_member_count(
            group
        )

        if member_count >= group.max_members:
            continue

        match_score = _calculate_match_score(
            group=group,
            goal_id=goal_id,
            fitness_level=fitness_level,
            workout_type=workout_type,
            available_days=available_days,
            preferred_start_time=preferred_start_time,
            preferred_end_time=preferred_end_time,
            equipment=equipment,
        )

        if match_score < minimum_score:
            continue

        risk = analyze_group_risk(
            user=user,
            group=group,
            persist=False,
            additional_injuries=temporary_injuries,
        )

        if risk["level"] == RiskLevel.HIGH:
            continue

        recommendations.append(
            {
                "group": group,
                "member_count": member_count,
                "match_score": match_score,
                "risk": risk,
            }
        )

    recommendations.sort(
        key=lambda item: (
            -item["match_score"],
            item["risk"]["score"],
            item["group"].id,
        )
    )

    return recommendations[:limit]