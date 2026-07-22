import os

import mongoengine
from django.apps import AppConfig
from mongoengine.connection import get_connection


class TeamConfig(AppConfig):
    """
    Django application configuration for team2.

    Establishes the default MongoEngine connection when Django starts.
    """

    default_auto_field = "django.db.models.BigAutoField"
    # Updated to point to the correct team2 package    
    name = "teams.team2"
    label = "team2"

    def ready(self):
        """
        Connect MongoEngine to the team database once per process.

        MONGO_DATABASE_URL must contain the full MongoDB connection URI.
        """

        if os.environ.get("TESTING") == "1":
            return

        # Retrieve MongoDB connection string from MONGO_DATABASE_URL environment variable
        database_url = os.environ.get("MONGO_DATABASE_URL")

        if not database_url:
            raise RuntimeError("MONGO_DATABASE_URL is not configured")

        try:
            get_connection(alias="default")
        except mongoengine.ConnectionFailure:
            mongoengine.connect(
                db="team2_db",
                host=database_url,
                alias="default",
                uuidRepresentation="standard",
            )
