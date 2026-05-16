import logging

import requests as http_requests

from django.conf import settings
from django.http import JsonResponse

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .apps import RouteConfig
from .serializers import (
    RouteRequestSerializer,
    RouteResponseSerializer,
)

from .services.bootstrap import BootstrapState
from .services.optimizer import (
    RouteOptimizationError,
)

logger = logging.getLogger(__name__)


def services_ready() -> bool:
    """
    Real readiness check based on initialized services,
    not process-local bootstrap booleans.
    """

    return all([
        RouteConfig.geocoding_service is not None,
        RouteConfig.fuel_station_index is not None,
        RouteConfig.routing_service is not None,
        RouteConfig.fuel_optimizer is not None,
    ])


def health_check(_request):
    """
    Health endpoint used by Render.
    """

    if BootstrapState.error:
        return JsonResponse(
            {
                "status": "failed",
                "services_ready": False,
                "error": BootstrapState.error,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if services_ready():
        return JsonResponse(
            {
                "status": "ok",
                "services_ready": True,
            },
            status=status.HTTP_200_OK,
        )

    return JsonResponse(
        {
            "status": "starting",
            "services_ready": False,
        },
        status=status.HTTP_200_OK,
    )


class RouteView(APIView):
    """
    Route optimization endpoint.
    """

    def post(self, request: Request) -> Response:

        serializer = RouteRequestSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = serializer.validated_data[
            "start"
        ].strip()

        end = serializer.validated_data[
            "end"
        ].strip()

        # ---------------------------------------------------------
        # Ensure services are ready
        # ---------------------------------------------------------
        if not services_ready():

            if BootstrapState.error:
                return Response(
                    {
                        "error": BootstrapState.error,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "error": (
                        "Services are still starting. "
                        "Please retry in 30-60 seconds."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        routing_service = (
            RouteConfig.routing_service
        )

        fuel_station_index = (
            RouteConfig.fuel_station_index
        )

        fuel_optimizer = (
            RouteConfig.fuel_optimizer
        )

        try:
            # ---------------------------------------------------------
            # Get route
            # ---------------------------------------------------------
            route_result = routing_service.get_route(
                start,
                end,
            )

            # ---------------------------------------------------------
            # Nearby stations
            # ---------------------------------------------------------
            nearby_stations = (
                fuel_station_index.find_near_route(
                    route_coords=route_result.coords,
                    route_cum_miles=(
                        route_result.cum_miles
                    ),
                    max_off_route_miles=(
                        settings.MAX_OFF_ROUTE_MILES
                    ),
                )
            )

            logger.info(
                "Found %d nearby stations",
                len(nearby_stations),
            )

            # ---------------------------------------------------------
            # Optimize fuel stops
            # ---------------------------------------------------------
            optimization_result = (
                fuel_optimizer.optimize(
                    candidate_stations=(
                        nearby_stations
                    ),
                    total_route_miles=(
                        route_result.total_miles
                    ),
                )
            )

        except ValueError as exc:

            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except RouteOptimizationError as exc:

            return Response(
                {"error": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except http_requests.HTTPError as exc:

            logger.error(
                "Mapbox API error: %s",
                exc,
            )

            return Response(
                {
                    "error": (
                        f"Upstream routing API error: {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception:

            logger.exception(
                "Unexpected route processing failure"
            )

            return Response(
                {
                    "error": "Internal server error"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ---------------------------------------------------------
        # Response payload
        # ---------------------------------------------------------
        response_data = {
            "start": start,
            "end": end,
            "total_miles": round(
                route_result.total_miles,
                1,
            ),
            "duration_hours": round(
                route_result.duration_sec / 3600,
                2,
            ),
            "route": [
                {
                    "lat": lat,
                    "lon": lon,
                }
                for lat, lon in route_result.coords[::5]
            ],
            "fuel_stops": [
                {
                    "station_id": stop.station_id,
                    "name": stop.name,
                    "city": stop.city,
                    "state": stop.state,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "route_mile": stop.route_mile,
                    "off_route_miles": (
                        stop.off_route_miles
                    ),
                    "gallons_added": (
                        stop.gallons_added
                    ),
                    "price_per_gallon": (
                        stop.price_per_gallon
                    ),
                    "stop_cost": stop.stop_cost,
                }
                for stop in (
                    optimization_result.fuel_stops
                )
            ],
            "total_fuel_cost": (
                optimization_result.total_fuel_cost
            ),
            "total_gallons": (
                optimization_result.total_gallons
            ),
        }

        output_serializer = (
            RouteResponseSerializer(
                data=response_data
            )
        )

        output_serializer.is_valid(
            raise_exception=True
        )

        return Response(
            output_serializer.validated_data,
            status=status.HTTP_200_OK,
        )
