from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Import path of this app. `label` is the short name the core's database
    # router uses to send this team's models to its OWN database.
    name = "teams.team8"
    label = "team8"
    verbose_name = "PolyLife Social Network & LMS"

    def ready(self):
        # Register drf-spectacular's authentication extension.
        from . import schema  # noqa: F401
