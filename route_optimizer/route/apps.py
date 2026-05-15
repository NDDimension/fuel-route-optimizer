"""
Route app configuration.

IMPORTANT:
Do NOT perform expensive synchronous startup work directly in ready().

Render requires the app to bind to a port quickly.
Heavy initialization is delegated to a background bootstrap thread.
"""

from django.apps import AppConfig


class RouteConfig(AppConfig):
    name = "route"
    default_auto_field = "django.db.models.BigAutoField"

    geocoding_service = None
    fuel_station_index = None
    fuel_optimizer = None
    routing_service = None

    def ready(self):
        from route.services.bootstrap import bootstrap_services

        bootstrap_services(RouteConfig)
