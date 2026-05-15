"""
Route optimization API view.
"""

import logging

import requests as http_requests
from django.http import JsonResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .apps import RouteConfig
from .serializers import RouteRequestSerializer, RouteResponseSerializer
from .services.bootstrap import initialize_services
from .services.optimizer import RouteOptimizationError

logger = logging.getLogger(__name__)


def health_check(_request):
    """
    Lightweight health endpoint for Render.

    Returns 200 immediately so Render knows the app is alive,
    even if heavy services are still warming up.
    """
    return JsonResponse(
        {
            "status": "ok",
            "services_ready": RouteConfig.routing_service is not None,
        },
        status=status.HTTP_200_OK,
    )


class RouteView(APIView):

    def post(self, request: Request) -> Response:
        # --------------------------------------------------------------
        # Lazy initialize services on first request
        # --------------------------------------------------------------
        try:
            initialize_services()
        except Exception:
            logger.exception("Failed initializing route services.")
            return Response(
                {"error": "Failed to initialize backend services."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # --------------------------------------------------------------
        # Validate input
        # --------------------------------------------------------------
        serializer = RouteRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        start: str = serializer.validated_data["start"].strip()
        end: str = serializer.validated_data["end"].strip()

        routing_svc = RouteConfig.routing_service
        fuel_index = RouteConfig.fuel_station_index
        optimizer = RouteConfig.fuel_optimizer

        try:
            # ----------------------------------------------------------
            # Fetch route
            # ----------------------------------------------------------
            route_result = routing_svc.get_route(start, end)

            # ----------------------------------------------------------
            # Find nearby fuel stations
            # ----------------------------------------------------------
            from django.conf import settings

            nearby = fuel_index.find_near_route(
                route_coords=route_result.coords,
                route_cum_miles=route_result.cum_miles,
                max_off_route_miles=settings.MAX_OFF_ROUTE_MILES,
            )

            logger.info(
                "Found %d candidate fuel stations.",
                len(nearby),
            )

            # ----------------------------------------------------------
            # Optimize fuel stops
            # ----------------------------------------------------------
            opt_result = optimizer.optimize(
                candidate_stations=nearby,
                total_route_miles=route_result.total_miles,
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
            logger.error("Mapbox API error: %s", exc)

            return Response(
                {"error": f"Upstream routing API error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception:
            logger.exception("Unexpected error processing route request.")

            return Response(
                {"error": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # --------------------------------------------------------------
        # Response
        # --------------------------------------------------------------
        response_data = {
            "start": start,
            "end": end,
            "total_miles": round(route_result.total_miles, 1),
            "duration_hours": round(route_result.duration_sec / 3600, 2),
            "route": [
                {"lat": lat, "lon": lon}
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
                    "off_route_miles": stop.off_route_miles,
                    "gallons_added": stop.gallons_added,
                    "price_per_gallon": stop.price_per_gallon,
                    "stop_cost": stop.stop_cost,
                }
                for stop in opt_result.fuel_stops
            ],
            "total_fuel_cost": opt_result.total_fuel_cost,
            "total_gallons": opt_result.total_gallons,
        }

        out_serializer = RouteResponseSerializer(data=response_data)
        out_serializer.is_valid(raise_exception=True)

        return Response(
            out_serializer.validated_data,
            status=status.HTTP_200_OK,
        )
