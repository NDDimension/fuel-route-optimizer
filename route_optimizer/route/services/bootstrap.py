"""
Background bootstrapper for expensive startup services.

Why this exists:
- Render kills deployments if the app does not bind to a port quickly.
- Loading/geocoding thousands of stations inside AppConfig.ready()
  blocks startup for too long.
- We therefore bootstrap expensive services in a background thread.
"""

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


class BootstrapState:
    """
    Global bootstrap state.
    """

    started = False
    ready = False
    error = None


_bootstrap_lock = threading.Lock()


def bootstrap_services(route_config_cls):
    """
    Initialize all expensive services in a background thread.
    """

    with _bootstrap_lock:
        if BootstrapState.started:
            return

        BootstrapState.started = True

    def _run():
        try:
            if not settings.MAPBOX_TOKEN:
                raise RuntimeError(
                    "MAPBOX_TOKEN environment variable is missing."
                )

            from route.services.geocoding import GeocodingService
            from route.services.fuel import load_fuel_stations
            from route.services.routing import RoutingService
            from route.services.optimizer import FuelOptimizer

            logger.info("=== Route Optimizer bootstrap started ===")

            # ------------------------------------------------------------------
            # 1. Geocoding service
            # ------------------------------------------------------------------
            route_config_cls.geocoding_service = GeocodingService()

            logger.info("Geocoding service initialized")

            # ------------------------------------------------------------------
            # 2. Fuel station index
            # ------------------------------------------------------------------
            route_config_cls.fuel_station_index = load_fuel_stations(
                csv_path=settings.FUEL_CSV_PATH,
                geocoding_service=route_config_cls.geocoding_service,
            )

            logger.info("Fuel station index loaded")

            # ------------------------------------------------------------------
            # 3. Routing service
            # ------------------------------------------------------------------
            route_config_cls.routing_service = RoutingService(
                geocoding_service=route_config_cls.geocoding_service
            )

    thread.start()
