"""
Routes every /api/... path to its controller function.
Owned by the Controller person since routing is part of
'HTTP request processing'.
"""

from django.urls import path
from . import controllers

urlpatterns = [
    # Progress Tracking
    path("physical-data/", controllers.register_physical_data, name="register_physical_data"),
    path("physical-data/<str:record_id>/edit/", controllers.edit_physical_data, name="edit_physical_data"),
    path("physical-data/<str:record_id>/delete/", controllers.delete_physical_data, name="delete_physical_data"),
    path("progress-charts/", controllers.get_progress_charts, name="get_progress_charts"),
    path("goals/", controllers.set_goal, name="set_goal"),
    path("mentor-report/<str:athlete_id>/", controllers.get_mentor_report, name="get_mentor_report"),

    # Reminder & Notification
    path("reminders/", controllers.create_reminder, name="create_reminder"),
    path("reminders/<str:reminder_id>/edit/", controllers.edit_reminder, name="edit_reminder"),
    path("reminders/<str:reminder_id>/delete/", controllers.delete_reminder, name="delete_reminder"),
    path("notification-settings/", controllers.update_notification_settings, name="update_notification_settings"),
    path("notifications/history/", controllers.get_notification_history, name="get_notification_history"),
    path("events/subscribe/", controllers.subscribe_to_event, name="subscribe_to_event"),
    path("mentor-message/", controllers.send_mentor_message, name="send_mentor_message"),
]