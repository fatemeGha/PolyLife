import os
import mongoengine
from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "teams.team7"
    label = "team7"

    def ready(self):
        mongoengine.connect(host=os.environ.get("DATABASE_URL"))