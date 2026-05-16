from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class RouteConfig(AppConfig):
    name = "route"

    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    geocoding_service = None
    fuel_station_index = None
    fuel_optimizer = None
    routing_service = None

    def ready(self):
        logger.info(
            "RouteConfig.ready() called"
        )

        from route.services.bootstrap import (
            bootstrap_services,
        )

        bootstrap_services(RouteConfig)
