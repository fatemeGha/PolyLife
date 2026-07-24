from rest_framework import status


class Team6ServiceError(Exception):
    code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred."
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message=None,
        *,
        details=None,
    ):
        self.message = message or self.message
        self.details = details or {}

        super().__init__(self.message)


class AuthHeadersMissingError(Team6ServiceError):
    code = "AUTH_HEADERS_MISSING"
    message = "User authentication headers are missing."
    status_code = status.HTTP_401_UNAUTHORIZED


class ValidationServiceError(Team6ServiceError):
    code = "VALIDATION_ERROR"
    message = "The request data is invalid."
    status_code = status.HTTP_400_BAD_REQUEST


class ProfileNotFoundError(Team6ServiceError):
    code = "PROFILE_NOT_FOUND"
    message = "Fitness profile was not found."
    status_code = status.HTTP_404_NOT_FOUND


class ProfileAlreadyExistsError(Team6ServiceError):
    code = "PROFILE_ALREADY_EXISTS"
    message = "A fitness profile already exists for this user."
    status_code = status.HTTP_409_CONFLICT


class ProfileIncompleteError(Team6ServiceError):
    code = "PROFILE_INCOMPLETE"
    message = "The fitness profile is incomplete."
    status_code = status.HTTP_400_BAD_REQUEST


class GoalNotFoundError(Team6ServiceError):
    code = "GOAL_NOT_FOUND"
    message = "Fitness goal was not found."
    status_code = status.HTTP_404_NOT_FOUND


class GroupNotFoundError(Team6ServiceError):
    code = "GROUP_NOT_FOUND"
    message = "Training group was not found."
    status_code = status.HTTP_404_NOT_FOUND


class GroupFullError(Team6ServiceError):
    code = "GROUP_FULL"
    message = "The training group has reached its maximum capacity."
    status_code = status.HTTP_409_CONFLICT


class AlreadyMemberError(Team6ServiceError):
    code = "ALREADY_MEMBER"
    message = "The user is already a member of this group."
    status_code = status.HTTP_409_CONFLICT


class HighRiskGroupError(Team6ServiceError):
    code = "HIGH_RISK_GROUP"
    message = (
        "Joining this group is not recommended "
        "because of high injury risk."
    )
    status_code = status.HTTP_409_CONFLICT


class MembershipNotFoundError(Team6ServiceError):
    code = "MEMBERSHIP_NOT_FOUND"
    message = "Group membership was not found."
    status_code = status.HTTP_404_NOT_FOUND