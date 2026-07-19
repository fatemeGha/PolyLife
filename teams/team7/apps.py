import os

import mongoengine
from django.apps import AppConfig
from mongoengine.connection import get_connection


class TeamConfig(AppConfig):
    """
    Django application configuration for team7.

    Establishes the default MongoEngine connection when Django starts.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "teams.team7"
    label = "team7"

    def ready(self):
        """
        Connect MongoEngine to the team database once per process.

        DATABASE_URL must contain the full MongoDB connection URI.
        """
        database_url = os.environ.get("DATABASE_URL")

        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")

        try:
            get_connection(alias="default")
        except mongoengine.ConnectionFailure:
            mongoengine.connect(
                db="team7_db",
                host=database_url,
                alias="default",
                uuidRepresentation="standard",
            )