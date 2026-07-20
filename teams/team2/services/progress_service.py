"""
Business logic for the Progress Tracking domain.

Rules enforced here:
    - BMI is always calculated automatically (weight / (height_m)^2)
    - Users can only access/modify their own records
    - Deletion is always soft (is_deleted = True)
    - UserGoal follows upsert semantics (one goal per user)
    - target_date must be today or in the future
    - Weight/height values must be within realistic bounds
      (enforced by model validators AND re-checked here for clear error messages)
    - Summary returns None gracefully when no records/goals exist
"""

from datetime import date

from ..models import PhysicalRecord, UserGoal


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

    if target_date is not None:
        try:
            parsed_date = date.fromisoformat(str(target_date))
            if parsed_date < date.today():
                errors["target_date"] = "Target date must be today or in the future."
        except (ValueError, TypeError):
            errors["target_date"] = "Invalid date format. Use YYYY-MM-DD."

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
        "id": record.id,
        "user_id": record.user_id,
        "weight": record.weight,
        "height": record.height,
        "bmi": record.bmi,
        "bmi_category": get_bmi_category(record.bmi),
        "body_fat_percentage": record.body_fat_percentage,
        "muscle_mass": record.muscle_mass,
        "notes": record.notes,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def serialize_goal(goal: UserGoal) -> dict:
    """
    Convert a UserGoal model instance to a JSON-serializable dict.

    Args:
        goal: UserGoal instance.

    Returns:
        dict: Serialized representation.
    """
    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "target_weight": goal.target_weight,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "target_body_fat": goal.target_body_fat,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Progress Record Services
# ---------------------------------------------------------------------------

def create_physical_record(user_id: int, weight: float, height: float,
                            body_fat: float = None, muscle_mass: float = None,
                            notes: str = "") -> tuple[bool, dict, str]:
    """
    Create and persist a new physical record for the given user.

    Steps:
        1. Validate input values.
        2. Calculate BMI automatically.
        3. Save record to database.

    Args:
        user_id     : Authenticated user's ID (from Gateway header).
        weight      : Body weight in kg.
        height      : Height in cm.
        body_fat    : Body fat percentage (optional).
        muscle_mass : Muscle mass in kg (optional).
        notes       : Optional free-text notes.

    Returns:
        tuple: (success: bool, data: dict, message: str)
            - On success: (True, serialized_record, success_message)
            - On failure: (False, error_dict, error_message)
    """
    # Step 1: validate
    errors = validate_physical_record_data(weight, height, body_fat, muscle_mass)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Step 2: calculate BMI
    bmi = calculate_bmi(weight, height)

    # Step 3: persist
    record = PhysicalRecord.objects.create(
        user_id=user_id,
        weight=weight,
        height=height,
        bmi=bmi,
        body_fat_percentage=body_fat,
        muscle_mass=muscle_mass,
        notes=notes or "",
    )

    return True, serialize_record(record), "Physical record created successfully."


def get_user_records(user_id: int) -> list[dict]:
    """
    Retrieve all active (non-deleted) physical records for a user,
    ordered by creation date descending (newest first).

    Args:
        user_id: Authenticated user's ID.

    Returns:
        list: List of serialized record dicts.
    """
    records = PhysicalRecord.objects.filter(
        user_id=user_id,
        is_deleted=False,
    ).order_by("-created_at")

    return [serialize_record(r) for r in records]


def update_physical_record(user_id: int, record_id: int,
                            weight: float = None, height: float = None,
                            body_fat: float = None, muscle_mass: float = None,
                            notes: str = None) -> tuple[bool, dict, str]:
    """
    Update an existing physical record owned by the user.

    Ownership check: the record's user_id must match the requester's user_id.
    BMI is recalculated if weight or height changes.

    Args:
        user_id   : Authenticated user's ID.
        record_id : Primary key of the record to update.
        weight    : New weight (optional).
        height    : New height (optional).
        body_fat  : New body fat percentage (optional).
        muscle_mass: New muscle mass (optional).
        notes     : New notes (optional).

    Returns:
        tuple: (success: bool, data: dict, message: str)
    """
    # Fetch the record — must exist, belong to user, and not be deleted
    try:
        record = PhysicalRecord.objects.get(
            id=record_id,
            user_id=user_id,
            is_deleted=False,
        )
    except PhysicalRecord.DoesNotExist:
        return False, {}, "Record not found or you do not have permission to modify it."

    # Apply updates to only the provided fields
    new_weight = weight if weight is not None else record.weight
    new_height = height if height is not None else record.height

    # Validate the final values (combining old + new)
    new_body_fat = body_fat if body_fat is not None else record.body_fat_percentage
    new_muscle_mass = muscle_mass if muscle_mass is not None else record.muscle_mass

    errors = validate_physical_record_data(new_weight, new_height, new_body_fat, new_muscle_mass)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Recalculate BMI with final values
    record.weight = new_weight
    record.height = new_height
    record.bmi = calculate_bmi(new_weight, new_height)
    record.body_fat_percentage = new_body_fat
    record.muscle_mass = new_muscle_mass

    if notes is not None:
        record.notes = notes

    record.save()

    return True, serialize_record(record), "Physical record updated successfully."


def soft_delete_record(user_id: int, record_id: int) -> tuple[bool, dict, str]:
    """
    Soft-delete a physical record by setting is_deleted=True.

    The record is never physically removed from the database.
    Only the owner (matching user_id) can delete their records.

    Args:
        user_id   : Authenticated user's ID.
        record_id : Primary key of the record to delete.

    Returns:
        tuple: (success: bool, data: dict, message: str)
    """
    try:
        record = PhysicalRecord.objects.get(
            id=record_id,
            user_id=user_id,
            is_deleted=False,
        )
    except PhysicalRecord.DoesNotExist:
        return False, {}, "Record not found or you do not have permission to delete it."

    record.is_deleted = True
    record.save(update_fields=["is_deleted", "updated_at"])

    return True, {"id": record_id}, "Physical record deleted successfully."


# ---------------------------------------------------------------------------
# Goal Services
# ---------------------------------------------------------------------------

def upsert_user_goal(user_id: int, target_weight: float,
                     target_date=None, target_body_fat: float = None) -> tuple[bool, dict, str]:
    """
    Create or update the user's fitness goal (upsert semantics).

    Each user has at most ONE active goal. If one already exists,
    it is updated in-place. If not, a new one is created.

    Args:
        user_id        : Authenticated user's ID.
        target_weight  : Target body weight in kg.
        target_date    : Target date string (YYYY-MM-DD) or None.
        target_body_fat: Target body fat percentage (optional).

    Returns:
        tuple: (success: bool, data: dict, message: str)
    """
    # Validate inputs
    errors = validate_goal_data(target_weight, target_date)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Parse date if provided
    parsed_date = None
    if target_date:
        parsed_date = date.fromisoformat(str(target_date))

    # Upsert: update_or_create based on user_id
    goal, created = UserGoal.objects.update_or_create(
        user_id=user_id,
        defaults={
            "target_weight": target_weight,
            "target_date": parsed_date,
            "target_body_fat": target_body_fat,
            "is_deleted": False,          # reactivate if previously soft-deleted
        },
    )

    message = "Goal created successfully." if created else "Goal updated successfully."
    return True, serialize_goal(goal), message


# ---------------------------------------------------------------------------
# Progress Summary Service
# ---------------------------------------------------------------------------

def get_progress_summary(user_id: int) -> dict:
    """
    Build a progress summary for the user.

    Includes:
        - Latest physical record (current weight, BMI, body fat, muscle mass)
        - Active goal (target weight, target date)
        - Weight remaining to reach the goal
        - Progress percentage toward the goal

    Returns an empty/null-safe dict even when no records or goals exist.

    Args:
        user_id: Authenticated user's ID.

    Returns:
        dict: Summary data.
    """
    # Fetch latest active record
    latest_record = PhysicalRecord.objects.filter(
        user_id=user_id,
        is_deleted=False,
    ).order_by("-created_at").first()

    # Fetch active goal
    try:
        goal = UserGoal.objects.get(user_id=user_id, is_deleted=False)
    except UserGoal.DoesNotExist:
        goal = None

    # Build current status section
    current = None
    if latest_record:
        current = {
            "weight": latest_record.weight,
            "height": latest_record.height,
            "bmi": latest_record.bmi,
            "bmi_category": get_bmi_category(latest_record.bmi),
            "body_fat_percentage": latest_record.body_fat_percentage,
            "muscle_mass": latest_record.muscle_mass,
            "recorded_at": latest_record.created_at.isoformat(),
        }

    # Build goal section
    goal_data = None
    if goal:
        goal_data = {
            "target_weight": goal.target_weight,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "target_body_fat": goal.target_body_fat,
        }

    # Calculate progress toward goal
    progress = None
    if latest_record and goal:
        weight_remaining = round(latest_record.weight - goal.target_weight, 2)
        # Calculate percentage: how far from start toward goal
        # We do not know the starting weight here, so we show absolute difference
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
