from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Import path of this app. `label` is the short name the core's database
    # router uses to send this team's models to its OWN database.
    name = "teams.team4"
    label = "team4"
