"""
Management command: preload_fuel_data

Pre-warms the geocode SQLite cache so that server startup is fast in
production (and CI/CD pipelines can run this step separately from
server deployment).

Usage:
    python manage.py preload_fuel_data

This is the same logic that runs in AppConfig.ready(), but surfaced as a
management command so you can run it in a Docker build step, a cron job,
or a one-time init container — before traffic is routed to the server.

Exit codes:
    0 — success
    1 — failure (check stderr / logs)
"""

import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pre-geocode all fuel stations and cache results to disk."

    def handle(self, *args, **options):
        self.stdout.write("Loading fuel data and geocoding stations…")
        self.stdout.write(
            f"  CSV:   {settings.FUEL_CSV_PATH}\n"
            f"  Cache: {settings.GEOCODE_CACHE_PATH}\n"
        )

        if not settings.MAPBOX_TOKEN:
            self.stderr.write(self.style.ERROR("MAPBOX_TOKEN is not set."))
            sys.exit(1)

        try:
            from route.services.geocoding import GeocodingService
            from route.services.fuel import load_fuel_stations

            geo_svc = GeocodingService()
            index = load_fuel_stations(
                csv_path=settings.FUEL_CSV_PATH,
                geocoding_service=geo_svc,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. {len(index.stations)} stations indexed and ready."
                )
            )
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed: {exc}"))
            logger.exception("preload_fuel_data failed.")
            sys.exit(1)
