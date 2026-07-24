"""OpenAPI description for gateway-provided authentication."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class GatewayAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "teams.team8.authentication.GatewayHeaderAuthentication"
    name = "GatewayIdentity"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-User-Id",
            "description": (
                "Trusted identity header injected by Team 8 Nginx after Core verifies "
                "the JWT. Clients should send their Core cookie/Bearer token to the "
                "gateway instead of setting this header directly."
            ),
        }

