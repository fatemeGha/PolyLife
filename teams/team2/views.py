"""
Team2 microservice views.

Controllers are intentionally thin:
    - Parse and validate request structure (JSON body, query params)
    - Call the appropriate service function
    - Return a standardized JSON response

All domain/business logic lives in services/
"""

import json

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .utils.auth import gateway_auth_required, success_response, error_response
from .services import progress_service, reminder_service


# ---------------------------------------------------------------------------
# Utility: safe JSON body parser
# ---------------------------------------------------------------------------

def parse_json_body(request) -> tuple[dict | None, str | None]:
    """
    Safely parse the JSON body of an incoming request.

    Returns:
        (data_dict, None)       on success
        (None, error_message)   on failure
    """
    try:
        if not request.body:
            return {}, None
        data = json.loads(request.body.decode("utf-8"))
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object."
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Invalid JSON format in request body."


# ---------------------------------------------------------------------------
# Health check — no auth required (from phase 7.1, keep as-is)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def health_check(request):
    """
    GET /api/team2/health/
    Public health check. No authentication required.
    """
    return success_response(
        data={"service": "team2", "status": "healthy"},
        message="Service is running",
    )


# ---------------------------------------------------------------------------
# Auth test — from phase 7.1, keep as-is
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def auth_test(request):
    """
    GET /api/team2/auth-test/
    Protected test endpoint to verify Gateway authentication.
    """
    return success_response(
        data={
            "user_id": request.user_info["user_id"],
            "username": request.user_info["username"],
        },
        message="Authenticated successfully",
    )


# ---------------------------------------------------------------------------
# Physical Records
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def physical_records_list_create(request):
    """
    Handles both listing and creating physical records.

    GET  /api/team2/progress/records/
        Returns all active physical records for the authenticated user,
        ordered by creation date (newest first).

    POST /api/team2/progress/records/
        Creates a new physical record.
        Required fields: weight (kg), height (cm)
        Optional fields: body_fat_percentage, muscle_mass, notes

    Authentication: Gateway headers required (X-User-Id, X-User-Username)
    """
    user_id = request.user_info["user_id"]

    # ------------------------------------------------------------------
    # GET: list all records
    # ------------------------------------------------------------------
    if request.method == "GET":
        records = progress_service.get_user_records(user_id)
        return success_response(
            data={"records": records, "count": len(records)},
            message="Physical records retrieved successfully.",
        )

    # ------------------------------------------------------------------
    # POST: create a new record
    # ------------------------------------------------------------------
    if request.method == "POST":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        # Extract fields from body
        weight = body.get("weight")
        height = body.get("height")
        body_fat = body.get("body_fat_percentage")
        muscle_mass = body.get("muscle_mass")
        notes = body.get("notes", "")

        success, data, message = progress_service.create_physical_record(
            user_id=user_id,
            weight=weight,
            height=height,
            body_fat=body_fat,
            muscle_mass=muscle_mass,
            notes=notes,
        )

        if not success:
            return error_response(message=message, errors=data, status=400)

        return success_response(data=data, message=message, status=201)

    # ------------------------------------------------------------------
    # Method not allowed
    # ------------------------------------------------------------------
    return error_response(
        message="Method not allowed. Supported methods: GET, POST.",
        status=405,
    )


@csrf_exempt
@gateway_auth_required
def physical_record_detail(request, record_id: int):
    """
    Handles retrieving, updating, and soft-deleting a single physical record.

    PUT    /api/team2/progress/records/<id>/
        Updates the specified record.
        All fields are optional — only provided fields are updated.

    DELETE /api/team2/progress/records/<id>/
        Soft-deletes the specified record (sets is_deleted=True).
        The record is NOT physically removed from the database.

    Ownership: Users can only modify/delete their own records.
    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]

    # ------------------------------------------------------------------
    # PUT: update record
    # ------------------------------------------------------------------
    if request.method == "PUT":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        success, data, message = progress_service.update_physical_record(
            user_id=user_id,
            record_id=record_id,
            weight=body.get("weight"),
            height=body.get("height"),
            body_fat=body.get("body_fat_percentage"),
            muscle_mass=body.get("muscle_mass"),
            notes=body.get("notes"),
        )

        if not success:
            status_code = 404 if not data else 400
            return error_response(message=message, errors=data, status=status_code)

        return success_response(data=data, message=message)

    # ------------------------------------------------------------------
    # DELETE: soft delete
    # ------------------------------------------------------------------
    if request.method == "DELETE":
        success, data, message = progress_service.soft_delete_record(
            user_id=user_id,
            record_id=record_id,
        )

        if not success:
            return error_response(message=message, status=404)

        return success_response(data=data, message=message)

    # ------------------------------------------------------------------
    # Method not allowed
    # ------------------------------------------------------------------
    return error_response(
        message="Method not allowed. Supported methods: PUT, DELETE.",
        status=405,
    )


# ---------------------------------------------------------------------------
# User Goal
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def user_goal(request):
    """
    Handles creating or updating the authenticated user's fitness goal.

    POST /api/team2/progress/goals/
        Creates a new goal or updates the existing one (upsert semantics).
        Each user can have only ONE active goal at a time.

        Required fields: target_weight (kg)
        Optional fields: target_date (YYYY-MM-DD), target_body_fat (%)

    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]

    if request.method == "POST":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        success, data, message = progress_service.upsert_user_goal(
            user_id=user_id,
            target_weight=body.get("target_weight"),
            target_date=body.get("target_date"),
            target_body_fat=body.get("target_body_fat"),
        )

        if not success:
            return error_response(message=message, errors=data, status=400)

        return success_response(data=data, message=message, status=201)

    return error_response(
        message="Method not allowed. Supported method: POST.",
        status=405,
    )


# ---------------------------------------------------------------------------
# Progress Summary
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def progress_summary(request):
    """
    GET /api/team2/progress/summary/

    Returns a progress summary for the authenticated user.
    """
    user_id = request.user_info["user_id"]
    summary = progress_service.get_progress_summary(user_id)

    return success_response(
        data=summary,
        message="Progress summary retrieved successfully.",
    )


# ---------------------------------------------------------------------------
# Reminders — List & Create (New in Phase 7.3)
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def reminder_list_create(request):
    """
    Handles listing and creating reminders for the authenticated user.

    GET  /api/team2/reminders/
        Returns all active (non-deleted, non-completed) reminders.
        Query param: ?include_completed=true  → include completed reminders.

    POST /api/team2/reminders/
        Creates a new reminder.

        Required fields:
            title          (string)
            reminder_time  (HH:MM or HH:MM:SS)

        Optional fields:
            message                  (string, default: "")
            recurrence_pattern       (none | daily | weekly, default: none)
            force_send_in_quiet_hours (bool, default: false)

        Quiet Hours Behavior:
            If the reminder_time falls within the user's quiet hours AND
            force_send_in_quiet_hours is false, the request is rejected with
            HTTP 409 and a detailed warning showing the quiet window.

    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]

    # ------------------------------------------------------------------
    # GET: list reminders
    # ------------------------------------------------------------------
    if request.method == "GET":
        include_completed = request.GET.get("include_completed", "").lower() == "true"
        reminders = reminder_service.get_user_reminders(user_id, include_completed)
        return success_response(
            data={"reminders": reminders, "count": len(reminders)},
            message="Reminders retrieved successfully.",
        )

    # ------------------------------------------------------------------
    # POST: create reminder
    # ------------------------------------------------------------------
    if request.method == "POST":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        force = bool(body.get("force_send_in_quiet_hours", False))

        success, data, message = reminder_service.create_reminder(
            user_id=user_id,
            title=body.get("title"),
            reminder_time_str=body.get("reminder_time"),
            recurrence_pattern=body.get("recurrence_pattern", "none"),
            message=body.get("message", ""),
            force=force,
        )

        if not success:
            # Quiet hours conflict → 409, validation error → 400
            status_code = 409 if "quiet_hours_conflict" in data else 400
            return error_response(message=message, errors=data, status=status_code)

        return success_response(data=data, message=message, status=201)

    return error_response(
        message="Method not allowed. Supported methods: GET, POST.",
        status=405,
    )


# ---------------------------------------------------------------------------
# Reminders — Detail (Update / Delete) (New in Phase 7.3)
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def reminder_detail(request, reminder_id: int):
    """
    Handles updating and soft-deleting a single reminder.

    PUT    /api/team2/reminders/<id>/
        Partial update — only provided fields are changed.
        Re-validates quiet hours if reminder_time changes.

    DELETE /api/team2/reminders/<id>/
        Soft-deletes the reminder (is_deleted=True, is_active=False).

    Ownership: Users can only modify their own reminders.
    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]

    # ------------------------------------------------------------------
    # PUT: update reminder
    # ------------------------------------------------------------------
    if request.method == "PUT":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        force = bool(body.get("force_send_in_quiet_hours", False))

        success, data, message = reminder_service.update_reminder(
            user_id=user_id,
            reminder_id=reminder_id,
            title=body.get("title"),
            reminder_time_str=body.get("reminder_time"),
            recurrence_pattern=body.get("recurrence_pattern"),
            message=body.get("message"),
            is_active=body.get("is_active"),
            force=force,
        )

        if not success:
            status_code = 404 if not data else (
                409 if "quiet_hours_conflict" in data else 400
            )
            return error_response(message=message, errors=data, status=status_code)

        return success_response(data=data, message=message)

    # ------------------------------------------------------------------
    # DELETE: soft delete
    # ------------------------------------------------------------------
    if request.method == "DELETE":
        success, data, message = reminder_service.soft_delete_reminder(
            user_id=user_id,
            reminder_id=reminder_id,
        )

        if not success:
            return error_response(message=message, status=404)

        return success_response(data=data, message=message)

    return error_response(
        message="Method not allowed. Supported methods: PUT, DELETE.",
        status=405,
    )


# ---------------------------------------------------------------------------
# Reminders — Mark as Completed (New in Phase 7.3)
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def reminder_complete(request, reminder_id: int):
    """
    PATCH /api/team2/reminders/<id>/complete/

    Marks the specified reminder as completed.
    No request body required.
    """
    user_id = request.user_info["user_id"]

    if request.method == "PATCH":
        success, data, message = reminder_service.complete_reminder(
            user_id=user_id,
            reminder_id=reminder_id,
        )

        if not success:
            status_code = 404 if not data else 400
            return error_response(message=message, errors=data, status=status_code)

        return success_response(data=data, message=message)

    return error_response(
        message="Method not allowed. Supported method: PATCH.",
        status=405,
    )


# ---------------------------------------------------------------------------
# Notification Settings (New in Phase 7.3)
# ---------------------------------------------------------------------------

@csrf_exempt
@gateway_auth_required
def notification_settings(request):
    """
    Handles retrieving and updating notification preferences.

    GET /api/team2/notification-settings/
        Returns current settings (creates defaults on first access).

    PUT /api/team2/notification-settings/
        Updates settings fields.

    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]

    # ------------------------------------------------------------------
    # GET: retrieve settings
    # ------------------------------------------------------------------
    if request.method == "GET":
        success, data, message = reminder_service.get_notification_settings(user_id)
        return success_response(data=data, message=message)

    # ------------------------------------------------------------------
    # PUT: update settings
    # ------------------------------------------------------------------
    if request.method == "PUT":
        body, parse_error = parse_json_body(request)
        if parse_error:
            return error_response(message=parse_error, status=400)

        success, data, message = reminder_service.update_notification_settings(
            user_id=user_id,
            is_enabled=body.get("is_enabled"),
            quiet_hours_start_str=body.get("quiet_hours_start"),
            quiet_hours_end_str=body.get("quiet_hours_end"),
        )

        if not success:
            return error_response(message=message, errors=data, status=400)

        return success_response(data=data, message=message)

    return error_response(
        message="Method not allowed. Supported methods: GET, PUT.",
        status=405,
    )


# ---------------------------------------------------------------------------
# Notification History (New in Phase 7.3)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def notification_history(request):
    """
    GET /api/team2/notifications/history/

    Returns the authenticated user's notification audit log.
    """
    user_id = request.user_info["user_id"]
    status_filter = request.GET.get("status")

    success, data, message = reminder_service.get_notification_history(
        user_id=user_id,
        status_filter=status_filter,
    )

    if not success:
        return error_response(message=message, status=400)

    return success_response(
        data={"notifications": data, "count": len(data)},
        message=message,
    )


# ---------------------------------------------------------------------------
# Custom 404 handler
# ---------------------------------------------------------------------------

def not_found(request, exception=None):
    """Custom 404 handler for team2 API."""
    return error_response(
        message="The requested endpoint does not exist.",
        errors={"path": f"No route matched: {request.path}"},
        status=404,
    )

# ---------------------------------------------------------------------------
# Chart Data (New in Phase 9)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def chart_data(request):
    """
    GET /api/team2/progress/charts/

    Returns time-series data points for a single physical metric,
    suitable for rendering line/bar charts on the front-end.

    Query parameters (both required):
        metric : One of — weight | bmi | body_fat_percentage | muscle_mass
        period : One of — weekly | monthly | yearly

    Response shape:
        {
            "success": true,
            "message": "...",
            "data": {
                "metric": "weight",
                "period": "monthly",
                "period_days": 30,
                "unit": "kg",
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
                "count": 12,
                "points": [
                    {"date": "YYYY-MM-DD", "value": 80.5},
                    ...
                ]
            }
        }

    Error responses:
        400 — invalid or missing query parameters
        401 — missing Gateway auth headers

    Authentication: Gateway headers required (X-User-Id, X-User-Username).
    """
    user_id = request.user_info["user_id"]

    metric = request.GET.get("metric", "").strip().lower()
    period = request.GET.get("period", "").strip().lower()

    success, data, message = progress_service.get_chart_data(
        user_id=user_id,
        metric=metric,
        period=period,
    )

    if not success:
        return error_response(message=message, errors=data, status=400)

    return success_response(data=data, message=message)


# ---------------------------------------------------------------------------
# Trainer — View Student Progress (New in Phase 9)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
@gateway_auth_required
def trainer_student_progress(request, student_id: int):
    """
    GET /api/team2/trainer/users/<student_id>/progress/

    Allows an authenticated trainer to view the progress summary of a
    specific student identified by student_id.

    The response format is identical to GET /api/team2/progress/summary/
    but scoped to the requested student's data.

    Path parameter:
        student_id (int) : The user_id of the student to inspect.

    Design note:
        This endpoint trusts that the requester is a trainer.
        Role-based access control (RBAC) is intentionally left to
        the Gateway / Core service layer. This microservice does not
        manage roles — it only serves data.

    Error responses:
        400 — invalid student_id (non-positive integer)
        401 — missing Gateway auth headers
        404 — student has no data (empty summary)

    Authentication: Gateway headers required.
    """
    # Basic sanity check on the path parameter
    if student_id <= 0:
        return error_response(
            message="Invalid student_id. Must be a positive integer.",
            errors={"student_id": "Must be a positive integer greater than 0."},
            status=400,
        )

    summary = progress_service.get_progress_summary(user_id=student_id)

    # If the student has no records at all, return 404 to signal
    # the trainer that this student has not logged any data yet.
    if summary.get("current") is None and summary.get("goal") is None:
        return error_response(
            message=f"No progress data found for student with ID {student_id}.",
            errors={"student_id": "Student has not recorded any physical data yet."},
            status=404,
        )

    return success_response(
        data=summary,
        message=f"Progress summary for student {student_id} retrieved successfully.",
    )

