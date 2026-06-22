from django.test import TestCase, override_settings
from django.urls import reverse


class MicroservicesEndpointTests(TestCase):
    @override_settings(TEAM_APPS=[])
    def test_returns_decoy_when_no_teams(self):
        resp = self.client.get(reverse("core:microservices"))

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertGreater(len(body["microservices"]), 0)
        # All decoy entries are flagged as not implemented.
        self.assertTrue(all(m["implemented"] is False for m in body["microservices"]))

    @override_settings(TEAM_APPS=["team1", "team2"])
    def test_lists_real_teams_when_configured(self):
        resp = self.client.get(reverse("core:microservices"))

        body = resp.json()
        slugs = [m["slug"] for m in body["microservices"]]
        self.assertEqual(slugs, ["team1", "team2"])
        self.assertTrue(all(m["implemented"] is True for m in body["microservices"]))
        self.assertEqual(body["microservices"][0]["url"], "/team1/")
