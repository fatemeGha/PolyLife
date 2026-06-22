from django.test import TestCase, override_settings

from core.db_router import TeamPerAppRouter


class _FakeModel:
    """Stand-in for a model: the router only looks at _meta.app_label."""

    def __init__(self, app_label):
        self._meta = type("Meta", (), {"app_label": app_label})


class TeamPerAppRouterTests(TestCase):
    def setUp(self):
        self.router = TeamPerAppRouter()

    @override_settings(TEAM_APPS=["team1", "team2"])
    def test_team_model_routed_to_its_own_db(self):
        model = _FakeModel("team1")
        self.assertEqual(self.router.db_for_read(model), "team1")
        self.assertEqual(self.router.db_for_write(model), "team1")

    @override_settings(TEAM_APPS=["team1"])
    def test_core_model_uses_default(self):
        model = _FakeModel("core")
        self.assertIsNone(self.router.db_for_read(model))
        self.assertIsNone(self.router.db_for_write(model))

    @override_settings(TEAM_APPS=["team1", "team2"])
    def test_team_tables_migrate_only_into_their_db(self):
        self.assertTrue(self.router.allow_migrate("team1", "team1"))
        self.assertFalse(self.router.allow_migrate("default", "team1"))
        self.assertFalse(self.router.allow_migrate("team2", "team1"))

    @override_settings(TEAM_APPS=["team1"])
    def test_core_tables_migrate_only_into_default(self):
        self.assertTrue(self.router.allow_migrate("default", "core"))
        self.assertFalse(self.router.allow_migrate("team1", "core"))

    @override_settings(TEAM_APPS=["team1", "team2"])
    def test_relations_allowed_only_within_same_db(self):
        self.assertTrue(self.router.allow_relation(_FakeModel("team1"), _FakeModel("team1")))
        self.assertFalse(self.router.allow_relation(_FakeModel("team1"), _FakeModel("team2")))
        # Two core/built-in models both resolve to "default".
        self.assertTrue(self.router.allow_relation(_FakeModel("core"), _FakeModel("auth")))
