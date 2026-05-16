import logging
import sys
import threading
import time
import traceback

from django.conf import settings

logger = logging.getLogger(__name__)


def _log(msg: str, *args) -> None:
    """Log and immediately flush so Render shows output in real-time."""
    logger.info(msg, *args)
    sys.stdout.flush()
    sys.stderr.flush()


class BootstrapState:
    started = False
    ready = False
    error = None


_bootstrap_lock = threading.Lock()


def bootstrap_services(route_config_cls):
    """
    Load all services synchronously so the gunicorn worker won't accept
    requests until everything is ready.  The 300-second gunicorn timeout
    is plenty for the ~30-60 s this takes with a warm geocode cache.
    """

    _log("bootstrap_services() entered")

    with _bootstrap_lock:

        if BootstrapState.started:
            _log("bootstrap already started — skipping")
            return

        BootstrapState.started = True

    _log("Starting synchronous bootstrap...")
    t0 = time.monotonic()

    try:

        _log(
            "MAPBOX token exists: %s",
            bool(settings.MAPBOX_TOKEN),
        )

        _log("Importing GeocodingService...")
        from route.services.geocoding import (
            GeocodingService,
        )
        _log("Imported GeocodingService (%.1fs)", time.monotonic() - t0)

        _log("Importing fuel module (numpy/scipy)...")
        t1 = time.monotonic()
        from route.services.fuel import (
            load_fuel_stations,
        )
        _log("Imported load_fuel_stations (%.1fs)", time.monotonic() - t1)

        _log("Importing RoutingService...")
        from route.services.routing import (
            RoutingService,
        )
        _log("Imported RoutingService (%.1fs)", time.monotonic() - t0)

        _log("Importing FuelOptimizer...")
        from route.services.optimizer import (
            FuelOptimizer,
        )
        _log("Imported FuelOptimizer (%.1fs)", time.monotonic() - t0)

        _log(
            "=== All imports done (%.1fs). Initializing services... ===",
            time.monotonic() - t0,
        )

        route_config_cls.geocoding_service = (
            GeocodingService()
        )

        _log("Geocoding service initialized")

        _log(
            "Cache path: %s",
            settings.GEOCODE_CACHE_PATH,
        )

        _log(
            "Cache exists: %s",
            settings.GEOCODE_CACHE_PATH.exists(),
        )

        _log("Loading fuel stations (geocoding if cache is cold)...")
        t2 = time.monotonic()

        route_config_cls.fuel_station_index = (
            load_fuel_stations(
                csv_path=settings.FUEL_CSV_PATH,
                geocoding_service=(
                    route_config_cls.geocoding_service
                ),
            )
        )

        _log(
            "Fuel stations loaded (%.1fs)",
            time.monotonic() - t2,
        )

        route_config_cls.routing_service = (
            RoutingService(
                geocoding_service=(
                    route_config_cls.geocoding_service
                )
            )
        )

        _log("Routing service initialized")

        route_config_cls.fuel_optimizer = (
            FuelOptimizer()
        )

        _log("Fuel optimizer initialized")

        BootstrapState.ready = True

        _log(
            "=== Route Optimizer READY (total: %.1fs) ===",
            time.monotonic() - t0,
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
        sys.stdout.flush()
        sys.stderr.flush()
