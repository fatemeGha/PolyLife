from ..models import (
    DifficultyLevel,
    FitnessLevel,
    GroupExercise,
    InjuryHistory,
    InjurySeverity,
    RiskAnalysis,
    RiskLevel,
)


EXERCISE_RISK_SCORES = {
    RiskLevel.LOW: 10,
    RiskLevel.MEDIUM: 25,
    RiskLevel.HIGH: 40,
}

INJURY_SEVERITY_SCORES = {
    InjurySeverity.MILD: 10,
    InjurySeverity.MODERATE: 20,
    InjurySeverity.SEVERE: 35,
}

INTENSITY_SCORES = {
    "low": 0,
    "light": 0,
    "medium": 5,
    "moderate": 5,
    "high": 10,
    "intense": 10,
}

DIFFICULTY_SCORES = {
    DifficultyLevel.EASY: 10,
    DifficultyLevel.MEDIUM: 20,
    DifficultyLevel.HARD: 30,
}

WORKOUT_BODY_PARTS = {
    "running": {
        "knee",
        "ankle",
        "leg",
        "hip",
        "foot",
    },
    "cycling": {
        "knee",
        "leg",
        "hip",
        "back",
    },
    "swimming": {
        "shoulder",
        "back",
        "neck",
        "knee",
    },
    "yoga": {
        "back",
        "neck",
        "knee",
        "wrist",
        "shoulder",
    },
    "gym": {
        "back",
        "knee",
        "shoulder",
        "wrist",
        "elbow",
    },
    "hiit": {
        "knee",
        "ankle",
        "back",
        "shoulder",
    },
    "crossfit": {
        "back",
        "knee",
        "shoulder",
        "wrist",
        "elbow",
    },
    "home workout": {
        "back",
        "knee",
        "shoulder",
        "wrist",
    },
}


def _normalize_text(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def _normalize_body_part(value):
    body_part = _normalize_text(value)

    aliases = {
        "knees": "knee",
        "legs": "leg",
        "ankles": "ankle",
        "shoulders": "shoulder",
        "wrists": "wrist",
        "elbows": "elbow",
        "feet": "foot",
    }

    return aliases.get(body_part, body_part)


def _get_group_exercises(group):
    return list(
        GroupExercise.objects
        .filter(group=group)
        .select_related("exercise")
        .order_by("id")
    )


def _get_user_injuries(user):
    return list(
        InjuryHistory.objects
        .filter(user=user)
        .order_by("-injury_date", "-id")
    )


def _infer_exercise_body_parts(group, exercise):
    searchable_text = " ".join(
        [
            _normalize_text(group.workout_type),
            _normalize_text(exercise.type),
            _normalize_text(exercise.name),
        ]
    )

    body_parts = set()

    for workout_type, related_parts in WORKOUT_BODY_PARTS.items():
        if workout_type in searchable_text:
            body_parts.update(related_parts)

    return body_parts


def _injury_conflicts_with_exercise(
    injury,
    group,
    exercise,
):
    body_part = _normalize_body_part(injury.body_part)

    exercise_text = " ".join(
        [
            _normalize_text(exercise.name),
            _normalize_text(exercise.type),
        ]
    )

    if body_part and body_part in exercise_text:
        return True

    inferred_body_parts = _infer_exercise_body_parts(
        group,
        exercise,
    )

    return body_part in inferred_body_parts


def _fitness_mismatch_score(user, group):
    user_level = user.fitness_level
    group_level = group.difficulty_level

    if (
        user_level == FitnessLevel.BEGINNER
        and group_level == DifficultyLevel.HARD
    ):
        return 20

    if (
        user_level == FitnessLevel.BEGINNER
        and group_level == DifficultyLevel.MEDIUM
    ):
        return 10

    if (
        user_level == FitnessLevel.INTERMEDIATE
        and group_level == DifficultyLevel.HARD
    ):
        return 10

    return 0


def _risk_level_from_score(score):
    if score >= 70:
        return RiskLevel.HIGH

    if score >= 40:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def _recommendation_for_level(level):
    if level == RiskLevel.HIGH:
        return (
            "Joining this group is not recommended because "
            "of high injury risk."
        )

    if level == RiskLevel.MEDIUM:
        return (
            "The user should exercise with reduced intensity "
            "and appropriate supervision."
        )

    return "This group is suitable for the user."


def analyze_group_risk(
    *,
    user,
    group,
    persist=True,
):
    group_exercises = _get_group_exercises(group)
    injuries = _get_user_injuries(user)

    if group_exercises:
        base_score = max(
            EXERCISE_RISK_SCORES.get(
                item.exercise.risk_level,
                10,
            )
            for item in group_exercises
        )
    else:
        base_score = DIFFICULTY_SCORES.get(
            group.difficulty_level,
            10,
        )

    score = base_score
    reasons = []

    fitness_score = _fitness_mismatch_score(
        user,
        group,
    )

    if fitness_score:
        score += fitness_score

        reasons.append(
            {
                "body_part": "",
                "exercise": group.name,
                "message": (
                    "The group difficulty may be too high "
                    "for the user's current fitness level."
                ),
            }
        )

    for injury in injuries:
        for group_exercise in group_exercises:
            exercise = group_exercise.exercise

            if not _injury_conflicts_with_exercise(
                injury,
                group,
                exercise,
            ):
                continue

            severity_score = INJURY_SEVERITY_SCORES.get(
                injury.severity,
                10,
            )

            exercise_score = EXERCISE_RISK_SCORES.get(
                exercise.risk_level,
                10,
            )

            additional_exercise_score = max(
                exercise_score - 10,
                0,
            )

            intensity_score = INTENSITY_SCORES.get(
                _normalize_text(group_exercise.intensity),
                0,
            )

            score += (
                severity_score
                + additional_exercise_score
                + intensity_score
            )

            reasons.append(
                {
                    "body_part": injury.body_part,
                    "exercise": exercise.name,
                    "message": (
                        f"The exercise may affect the user's "
                        f"{injury.body_part} injury."
                    ),
                }
            )

    score = min(max(int(score), 0), 100)
    level = _risk_level_from_score(score)
    recommendation = _recommendation_for_level(level)

    result = {
        "group_id": group.id,
        "score": score,
        "level": level,
        "is_safe": level != RiskLevel.HIGH,
        "reasons": reasons,
        "recommendation": recommendation,
    }

    if persist:
        RiskAnalysis.objects.create(
            user=user,
            group=group,
            risk_level=level,
            score=score,
            recommendation=recommendation,
        )

    return result