"""
Background bootstrapper for expensive startup services.
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
    Initialize expensive services in background thread.
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

            logger.info(
                "=== Route Optimizer bootstrap started ==="
            )

            # Geocoding service
            route_config_cls.geocoding_service = (
                GeocodingService()
            )

            logger.info(
                "Geocoding service initialized"
            )

            logger.info(
                "Cache path: %s",
                settings.GEOCODE_CACHE_PATH,
            )

            logger.info(
                "Cache exists: %s",
                settings.GEOCODE_CACHE_PATH.exists(),
            )
            
            # Fuel station index
            route_config_cls.fuel_station_index = (
                load_fuel_stations(
                    csv_path=settings.FUEL_CSV_PATH,
                    geocoding_service=(
                        route_config_cls.geocoding_service
                    ),
                )
            )

            logger.info(
                "Fuel station index loaded"
            )

            # Routing service
            route_config_cls.routing_service = (
                RoutingService(
                    geocoding_service=(
                        route_config_cls.geocoding_service
                    )
                )
            )

            logger.info(
                "Routing service initialized"
            )

            # Optimizer
            route_config_cls.fuel_optimizer = (
                FuelOptimizer()
            )

            logger.info(
                "Fuel optimizer initialized"
            )

            BootstrapState.ready = True

            logger.info(
                "=== Route Optimizer READY ==="
            )

        except Exception as exc:
            BootstrapState.error = str(exc)

            logger.exception(
                "Bootstrap failed"
            )

    thread = threading.Thread(
        target=_run,
        daemon=True,
    )

    thread.start()
