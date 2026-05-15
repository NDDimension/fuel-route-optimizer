"""
Route app configuration.

Keep startup lightweight for Render deployment.
Heavy services are lazy-loaded on first request instead of during boot.
"""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RouteConfig(AppConfig):
    name = "route"
    default_auto_field = "django.db.models.BigAutoField"

    # Shared singleton services
    geocoding_service = None
    fuel_station_index = None
    fuel_optimizer = None
    routing_service = None

    def ready(self) -> None:
        """
        Lightweight startup only.

        DO NOT preload fuel stations or geocode data here.
        Render kills deployments if startup takes too long before
        Gunicorn binds to the PORT.
        """
        logger.info("=== Route Optimizer app loaded ===")
