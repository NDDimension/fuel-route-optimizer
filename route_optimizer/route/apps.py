"""
Route app configuration.

AppConfig.ready() is the correct Django hook for one-time startup work.
We load and index the fuel station data here so it's in memory before
the first request arrives.

Singleton pattern: the FuelStationIndex, GeocodingService, and
FuelOptimizer are stored as module-level attributes on this AppConfig
instance so every view/service can import them from a single, stable
location (`from route.apps import RouteConfig`).

NOTE: ready() is called twice in development (due to Django's auto-reloader
spawning a subprocess).  The index is cheap to rebuild from the geocode
cache on the second call, so this is acceptable.
"""

import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class RouteConfig(AppConfig):
    name = "route"
    default_auto_field = "django.db.models.BigAutoField"

    # These are set in ready() and imported by views.
    geocoding_service = None
    fuel_station_index = None
    fuel_optimizer = None
    routing_service = None

    def ready(self) -> None:
        """
        Initialise all stateful services.

        Import order matters: geocoding → fuel (geocodes internally) →
        routing (depends on geocoding) → optimizer (stateless).
        """
        # Avoid double-init in Django dev reloader child process.
        if RouteConfig.fuel_station_index is not None:
            return

        if not settings.MAPBOX_TOKEN:
            logger.error(
                "MAPBOX_TOKEN is not configured. "
                "The /route/ endpoint will return errors until it is set."
            )
            return  # Don't crash on startup — let views return 503 instead.

        try:
            from route.services.geocoding import GeocodingService
            from route.services.fuel import load_fuel_stations
            from route.services.routing import RoutingService
            from route.services.optimizer import FuelOptimizer

            logger.info("=== Route Optimizer: initialising services ===")

            # 1. Geocoding service (backed by SQLite cache on disk).
            RouteConfig.geocoding_service = GeocodingService()

            # 2. Fuel station index — loads CSV, geocodes, builds KDTree.
            #    First run: ~30–90 s (geocoding); subsequent: ~2–5 s (cache).
            RouteConfig.fuel_station_index = load_fuel_stations(
                csv_path=settings.FUEL_CSV_PATH,
                geocoding_service=RouteConfig.geocoding_service,
            )

            # 3. Routing service — wraps Mapbox Directions API.
            RouteConfig.routing_service = RoutingService(
                geocoding_service=RouteConfig.geocoding_service
            )

            # 4. Fuel optimizer — stateless, no external dependencies.
            RouteConfig.fuel_optimizer = FuelOptimizer()

            logger.info("=== Route Optimizer: ready to serve requests ===")

        except Exception:
            logger.exception(
                "Route Optimizer failed to initialise. "
                "All /route/ requests will return 503 until the issue is fixed."
            )
