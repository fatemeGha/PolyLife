from django.test import TestCase


class HomeViewTests(TestCase):
    def test_root_serves_a_page(self):
        resp = self.client.get("/")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PolyLife")

    def test_client_side_route_is_caught_by_spa(self):
        # Unknown (non-API) paths fall through to the SPA catch-all, so a
        # browser refresh on /login still returns the app shell, not a 404.
        resp = self.client.get("/login")

        self.assertEqual(resp.status_code, 200)

    def test_api_routes_are_not_swallowed_by_catch_all(self):
        resp = self.client.get("/api/health/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
