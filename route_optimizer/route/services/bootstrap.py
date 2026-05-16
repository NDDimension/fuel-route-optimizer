import logging
import threading
import traceback

from django.conf import settings

logger = logging.getLogger(__name__)


class BootstrapState:
    started = False
    ready = False
    error = None


_bootstrap_lock = threading.Lock()


def bootstrap_services(route_config_cls):

    logger.info("bootstrap_services() entered")

    with _bootstrap_lock:

        logger.info("bootstrap lock acquired")

        if BootstrapState.started:
            logger.info("bootstrap already started")
            return

        BootstrapState.started = True

    def _run():

        logger.info("bootstrap thread started")

        try:

            logger.info(
                "MAPBOX token exists: %s",
                bool(settings.MAPBOX_TOKEN),
            )

            from route.services.geocoding import (
                GeocodingService,
            )

            logger.info(
                "Imported GeocodingService"
            )

            from route.services.fuel import (
                load_fuel_stations,
            )

            logger.info(
                "Imported load_fuel_stations"
            )

            from route.services.routing import (
                RoutingService,
            )

            logger.info(
                "Imported RoutingService"
            )

            from route.services.optimizer import (
                FuelOptimizer,
            )

            logger.info(
                "Imported FuelOptimizer"
            )

            logger.info(
                "=== Route Optimizer bootstrap started ==="
            )

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

            logger.info(
                "Before load_fuel_stations"
            )

            route_config_cls.fuel_station_index = (
                load_fuel_stations(
                    csv_path=settings.FUEL_CSV_PATH,
                    geocoding_service=(
                        route_config_cls.geocoding_service
                    ),
                )
            )

            logger.info(
                "After load_fuel_stations"
            )

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

            logger.error(
                "BOOTSTRAP FAILED: %s",
                exc,
            )

            logger.error(
                traceback.format_exc()
            )

    thread = threading.Thread(
        target=_run,
        daemon=True,
    )

    logger.info("starting bootstrap thread")

    thread.start()

    logger.info("bootstrap thread launched")
