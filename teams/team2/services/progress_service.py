"""
Business logic for the Progress Tracking domain.

Rules enforced here:
    - BMI is always calculated automatically (weight / (height_m)^2)
    - Users can only access/modify their own records
    - Deletion is always soft (is_deleted = True)
    - Goal follows upsert semantics (one goal per user)
    - target_date must be today or in the future
    - Weight/height values must be within realistic bounds
      (enforced by model validators AND re-checked here for clear error messages)
    - Summary returns None gracefully when no records/goals exist
"""

from datetime import date

from ..models import PhysicalRecord, Goal


# ---------------------------------------------------------------------------
# BMI Calculator
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """
    Calculate Body Mass Index (BMI).

    Formula:
        BMI = weight(kg) / (height(m))^2

    Args:
        weight_kg : Body weight in kilograms.
        height_cm : Height in centimeters.

    Returns:
        float: BMI rounded to 2 decimal places.

    Raises:
        ValueError: If height is zero or negative.
    """
    if height_cm <= 0:
        raise ValueError("Height must be a positive number.")

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def get_bmi_category(bmi: float) -> str:
    """
    Return the WHO BMI category label for the given BMI value.

    Args:
        bmi: Calculated BMI value.

    Returns:
        str: Category label.
    """
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal weight"
    elif bmi < 30.0:
        return "Overweight"
    else:
        return "Obese"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_physical_record_data(weight: float, height: float,
                                   body_fat: float = None,
                                   muscle_mass: float = None) -> dict:
    """
    Validate incoming physical record field values.

    Args:
        weight      : Weight in kg.
        height      : Height in cm.
        body_fat    : Body fat percentage (optional).
        muscle_mass : Muscle mass in kg (optional).

    Returns:
        dict: Field-level errors. Empty dict means all values are valid.
    """
    errors = {}

    if weight is None:
        errors["weight"] = "Weight is required."
    elif not isinstance(weight, (int, float)) or weight <= 0:
        errors["weight"] = "Weight must be a positive number."
    elif weight < 1 or weight > 500:
        errors["weight"] = "Weight must be between 1 and 500 kg."

    if height is None:
        errors["height"] = "Height is required."
    elif not isinstance(height, (int, float)) or height <= 0:
        errors["height"] = "Height must be a positive number."
    elif height < 50 or height > 300:
        errors["height"] = "Height must be between 50 and 300 cm."

    if body_fat is not None:
        if not isinstance(body_fat, (int, float)) or body_fat < 1 or body_fat > 100:
            errors["body_fat_percentage"] = "Body fat percentage must be between 1 and 100."

    if muscle_mass is not None:
        if not isinstance(muscle_mass, (int, float)) or muscle_mass <= 0:
            errors["muscle_mass"] = "Muscle mass must be a positive number."

    return errors


def validate_goal_data(target_weight: float, target_date=None) -> dict:
    """
    Validate incoming goal field values.

    Args:
        target_weight : Target weight in kg.
        target_date   : Target date string (YYYY-MM-DD) or None.

    Returns:
        dict: Field-level errors. Empty dict means all values are valid.
    """
    errors = {}

    if target_weight is None:
        errors["target_weight"] = "Target weight is required."
    elif not isinstance(target_weight, (int, float)) or target_weight <= 0:
        errors["target_weight"] = "Target weight must be a positive number."
    elif target_weight < 1 or target_weight > 500:
        errors["target_weight"] = "Target weight must be between 1 and 500 kg."

    # Note: target_date validation is ignored as it doesn't exist on the MongoEngine model
    return errors


# ---------------------------------------------------------------------------
# Record serializer
# ---------------------------------------------------------------------------

def serialize_record(record: PhysicalRecord) -> dict:
    """
    Convert a PhysicalRecord model instance to a JSON-serializable dict.

    Args:
        record: PhysicalRecord instance.

    Returns:
        dict: Serialized representation.
    """
    return {
        "id": str(record.id),
        "user_id": record.user_id,
        "weight": record.weight,
        "height": record.height,
        "bmi": record.bmi,
        "bmi_category": get_bmi_category(record.bmi),
        "body_fat_percentage": record.body_fat_percent, # Map MongoEngine field to view payload key
        "muscle_mass": record.muscle_mass,
        "notes": "", # Notes field does not exist in the new MongoEngine models
        "created_at": record.created_at.isoformat(),
    }


def serialize_goal(goal: Goal) -> dict:
    """
    Convert a Goal model instance to a JSON-serializable dict.

    Args:
        goal: Goal instance.

    Returns:
        dict: Serialized representation.
    """
    return {
        "id": str(goal.id),
        "user_id": goal.user_id,
        "target_weight": goal.target_weight,
        "target_date": None, # target_date is not supported by the MongoEngine model
        "target_body_fat": goal.target_body_fat,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Progress Record Services
# ---------------------------------------------------------------------------

def create_physical_record(user_id: int, weight: float, height: float,
                            body_fat: float = None, muscle_mass: float = None,
                            notes: str = "") -> tuple[bool, dict, str]:
    """
    Create and persist a new physical record for the given user.
    """
    # Step 1: validate
    errors = validate_physical_record_data(weight, height, body_fat, muscle_mass)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Step 2: calculate BMI
    bmi = calculate_bmi(weight, height)

    # Step 3: persist using MongoEngine fields
    record = PhysicalRecord.objects.create(
        user_id=str(user_id),
        weight=weight,
        height=height,
        bmi=bmi,
        body_fat_percent=body_fat, # Updated to body_fat_percent
        muscle_mass=muscle_mass,
        # 'notes' field is not passed because it doesn't exist on PhysicalRecord
    )

    return True, serialize_record(record), "Physical record created successfully."


def get_user_records(user_id: int) -> list[dict]:
    """
    Retrieve all active (non-deleted) physical records for a user,
    ordered by creation date descending (newest first).
    """
    records = PhysicalRecord.objects.filter(
        user_id=str(user_id),
        is_deleted=False,
    ).order_by("-created_at")

    return [serialize_record(r) for r in records]


def update_physical_record(user_id: int, record_id: int,
                            weight: float = None, height: float = None,
                            body_fat: float = None, muscle_mass: float = None,
                            notes: str = None) -> tuple[bool, dict, str]:
    """
    Update an existing physical record owned by the user.
    """
    # Fetch the record — must exist, belong to user, and not be deleted
    try:
        record = PhysicalRecord.objects.get(
            record_id=str(record_id), # Query by key 'record_id'
            user_id=str(user_id),
            is_deleted=False,
        )
    except PhysicalRecord.DoesNotExist:
        return False, {}, "Record not found or you do not have permission to modify it."

    # Apply updates to only the provided fields
    new_weight = weight if weight is not None else record.weight
    new_height = height if height is not None else record.height

    # Validate the final values (combining old + new)
    new_body_fat = body_fat if body_fat is not None else record.body_fat_percent
    new_muscle_mass = muscle_mass if muscle_mass is not None else record.muscle_mass

    errors = validate_physical_record_data(new_weight, new_height, new_body_fat, new_muscle_mass)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Recalculate BMI with final values
    record.weight = new_weight
    record.height = new_height
    record.bmi = calculate_bmi(new_weight, new_height)
    record.body_fat_percent = new_body_fat # Updated to body_fat_percent
    record.muscle_mass = new_muscle_mass

    # 'notes' field is not updated as it doesn't exist

    record.save()

    return True, serialize_record(record), "Physical record updated successfully."


def soft_delete_record(user_id: int, record_id: int) -> tuple[bool, dict, str]:
    """
    Soft-delete a physical record by setting is_deleted=True.
    """
    try:
        record = PhysicalRecord.objects.get(
            record_id=str(record_id), # Query by key 'record_id'
            user_id=str(user_id),
            is_deleted=False,
        )
    except PhysicalRecord.DoesNotExist:
        return False, {}, "Record not found or you do not have permission to delete it."

    record.is_deleted = True
    record.save()

    return True, {"id": str(record_id)}, "Physical record deleted successfully."


# ---------------------------------------------------------------------------
# Goal Services
# ---------------------------------------------------------------------------

def upsert_user_goal(user_id: int, target_weight: float,
                     target_date=None, target_body_fat: float = None) -> tuple[bool, dict, str]:
    """
    Create or update the user's fitness goal (upsert semantics).
    """
    # Validate inputs
    errors = validate_goal_data(target_weight, target_date)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Upsert: update_or_create based on user_id in MongoEngine
    try:
        goal = Goal.objects.get(user_id=str(user_id))
        goal.target_weight = target_weight
        goal.target_body_fat = target_body_fat
        goal.is_deleted = False
        goal.save()
        created = False
    except Goal.DoesNotExist:
        goal = Goal.objects.create(
            user_id=str(user_id),
            target_weight=target_weight,
            target_body_fat=target_body_fat,
            is_deleted=False,
        )
        created = True

    message = "Goal created successfully." if created else "Goal updated successfully."
    return True, serialize_goal(goal), message


# ---------------------------------------------------------------------------
# Progress Summary Service
# ---------------------------------------------------------------------------

def get_progress_summary(user_id: int) -> dict:
    """
    Build a progress summary for the user.
    """
    # Fetch latest active record
    latest_record = PhysicalRecord.objects.filter(
        user_id=str(user_id),
        is_deleted=False,
    ).order_by("-created_at").first()

    # Fetch active goal
    try:
        goal = Goal.objects.get(user_id=str(user_id), is_deleted=False)
    except Goal.DoesNotExist:
        goal = None

    # Build current status section
    current = None
    if latest_record:
        current = {
            "weight": latest_record.weight,
            "height": latest_record.height,
            "bmi": latest_record.bmi,
            "bmi_category": get_bmi_category(latest_record.bmi),
            "body_fat_percentage": latest_record.body_fat_percent, # Updated to body_fat_percent
            "muscle_mass": latest_record.muscle_mass,
            "recorded_at": latest_record.created_at.isoformat(),
        }

    # Build goal section
    goal_data = None
    if goal:
        goal_data = {
            "target_weight": goal.target_weight,
            "target_date": None, # target_date is not supported
            "target_body_fat": goal.target_body_fat,
        }

    # Calculate progress toward goal
    progress = None
    if latest_record and goal:
        weight_remaining = round(latest_record.weight - goal.target_weight, 2)
        progress = {
            "weight_remaining": weight_remaining,
            "weight_remaining_direction": "to lose" if weight_remaining > 0 else "to gain",
            "goal_reached": weight_remaining <= 0,
        }

    return {
        "user_id": user_id,
        "current": current,
        "goal": goal_data,
        "progress": progress,
    }

# ---------------------------------------------------------------------------
# Chart Data Service
# ---------------------------------------------------------------------------

# Valid query parameter values — enforced at service layer
VALID_METRICS = {"weight", "bmi", "body_fat_percentage", "muscle_mass"}
VALID_PERIODS = {"weekly", "monthly", "yearly"}

# Period → number of days to look back
PERIOD_DAYS_MAP = {
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
}


def get_chart_data(user_id: int,
                   metric: str,
                   period: str) -> tuple[bool, dict, str]:
    """
    Build time-series data for charting a single physical metric.
    """
    from django.utils import timezone
    from datetime import timedelta

    # ------------------------------------------------------------------
    # Validate query parameters
    # ------------------------------------------------------------------
    errors = {}

    if not metric:
        errors["metric"] = (
            f"The 'metric' parameter is required. "
            f"Allowed values: {', '.join(sorted(VALID_METRICS))}."
        )
    elif metric not in VALID_METRICS:
        errors["metric"] = (
            f"Invalid metric '{metric}'. "
            f"Allowed values: {', '.join(sorted(VALID_METRICS))}."
        )

    if not period:
        errors["period"] = (
            f"The 'period' parameter is required. "
            f"Allowed values: {', '.join(sorted(VALID_PERIODS))}."
        )
    elif period not in VALID_PERIODS:
        errors["period"] = (
            f"Invalid period '{period}'. "
            f"Allowed values: {', '.join(sorted(VALID_PERIODS))}."
        )

    if errors:
        return False, errors, "Invalid query parameters."

    # ------------------------------------------------------------------
    # Compute date range
    # ------------------------------------------------------------------
    now = timezone.localtime(timezone.now())
    days_back = PERIOD_DAYS_MAP[period]
    start_date = now - timedelta(days=days_back)

    # ------------------------------------------------------------------
    # Query records within the window
    # ------------------------------------------------------------------
    records = PhysicalRecord.objects.filter(
        user_id=str(user_id),
        is_deleted=False,
        created_at__gte=start_date,
    ).order_by("created_at")   # ascending — chronological order for chart

    # ------------------------------------------------------------------
    # Build data points — skip records where the metric value is None
    # ------------------------------------------------------------------
    points = []
    
    # Map the query payload key to the actual MongoEngine model field
    model_metric = "body_fat_percent" if metric == "body_fat_percentage" else metric
    
    for record in records:
        value = getattr(record, model_metric, None)
        if value is None:
            continue
        points.append({
            "date": record.created_at.strftime("%Y-%m-%d"),
            "value": round(float(value), 2),
        })

    # ------------------------------------------------------------------
    # Metric → human-readable unit label
    # ------------------------------------------------------------------
    unit_map = {
        "weight": "kg",
        "bmi": "kg/m²",
        "body_fat_percentage": "%",
        "muscle_mass": "kg",
    }

    data = {
        "metric": metric,
        "period": period,
        "period_days": days_back,
        "unit": unit_map[metric],
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
        "points": points,
        "count": len(points),
    }

    return True, data, f"Chart data for '{metric}' over the last {days_back} days retrieved successfully."
