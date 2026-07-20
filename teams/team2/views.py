"""
Team2 microservice views.

Controllers are intentionally thin:
    - Parse and validate request structure (JSON body, query params)
    - Call the appropriate service function
    - Return a standardized JSON response

All domain/business logic lives in services/progress_service.py
"""

import json

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .utils.auth import gateway_auth_required, success_response, error_response
from .services import progress_service


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
            # Distinguish between validation errors (400) and not-found (404)
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

    Returns a progress summary for the authenticated user:
        - Current weight, BMI, BMI category, body fat, muscle mass
        - Active fitness goal (target weight, target date)
        - Weight remaining to reach the goal
        - Whether the goal has been reached

    Returns null-safe data even when no records or goals exist yet.
    Authentication: Gateway headers required.
    """
    user_id = request.user_info["user_id"]
    summary = progress_service.get_progress_summary(user_id)

    return success_response(
        data=summary,
        message="Progress summary retrieved successfully.",
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
