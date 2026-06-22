"""
Database router for the per-team microservice architecture.

Every app listed in ``settings.TEAM_APPS`` is routed to a database whose alias
equals the app label (e.g. the ``team1`` app uses the ``team1`` database). The
core and Django's built-in apps stay in ``default``. This keeps each team's data
fully isolated — one team can never read or migrate into another team's DB.
"""

from django.conf import settings


class TeamPerAppRouter:
    def _db_for(self, model):
        label = model._meta.app_label
        return label if label in settings.TEAM_APPS else None

    def db_for_read(self, model, **hints):
        return self._db_for(model)

    def db_for_write(self, model, **hints):
        return self._db_for(model)

    def allow_relation(self, obj1, obj2, **hints):
        # Relations are only allowed within the same database.
        db1 = self._db_for(obj1) or "default"
        db2 = self._db_for(obj2) or "default"
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in settings.TEAM_APPS:
            # A team's tables live only in that team's database.
            return db == app_label
        # Core / built-in apps migrate only into the default database.
        return db == "default"
