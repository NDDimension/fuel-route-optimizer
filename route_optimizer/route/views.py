"""
Route optimization API view.

POST /route/

Orchestration order:
  1. Validate input (RouteRequestSerializer).
  2. Check that all services are ready (AppConfig singleton).
  3. Call RoutingService.get_route() — ONE Mapbox Directions API call.
  4. Call FuelStationIndex.find_near_route() — KDTree query, no I/O.
  5. Call FuelOptimizer.optimize() — in-memory algorithm, no I/O.
  6. Serialize and return the response.

Error taxonomy:
  400 — Bad input (validation errors, unresolvable location names).
  503 — Services not ready (missing MAPBOX_TOKEN or startup crash).
  502 — Upstream Mapbox API error.
  500 — Unexpected internal error.
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
from .services.optimizer import RouteOptimizationError

logger = logging.getLogger(__name__)


def health_check(_request):
    services_ready = (
        RouteConfig.routing_service is not None
        and RouteConfig.fuel_station_index is not None
        and RouteConfig.fuel_optimizer is not None
    )

    status_code = status.HTTP_200_OK if services_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JsonResponse(
        {
            "status": "ok" if services_ready else "starting",
            "services_ready": services_ready,
        },
        status=status_code,
    )


class RouteView(APIView):
    """
    POST /route/

    Request body (JSON):
        {
            "start": "New York, NY",
            "end":   "Los Angeles, CA"
        }

    Response (JSON):
        {
            "start":           "New York, NY",
            "end":             "Los Angeles, CA",
            "total_miles":     2789.4,
            "duration_hours":  40.1,
            "route":           [{"lat": 40.71, "lon": -74.01}, ...],
            "fuel_stops": [
                {
                    "station_id":      "7",
                    "name":            "WOODSHED OF BIG CABIN",
                    "city":            "Big Cabin",
                    "state":           "OK",
                    "lat":             36.54,
                    "lon":             -95.07,
                    "route_mile":      1423.2,
                    "off_route_miles": 0.8,
                    "gallons_added":   38.2,
                    "price_per_gallon": 3.007,
                    "stop_cost":       114.87
                },
                ...
            ],
            "total_fuel_cost": 843.21,
            "total_gallons":   284.1
        }
    """

    def post(self, request: Request) -> Response:
        # ------------------------------------------------------------------
        # 1. Validate input
        # ------------------------------------------------------------------
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start: str = serializer.validated_data["start"].strip()
        end: str = serializer.validated_data["end"].strip()

        # ------------------------------------------------------------------
        # 2. Check service readiness
        # ------------------------------------------------------------------
        if not self._services_ready():
            return Response(
                {
                    "error": (
                        "Route optimizer services are not available. "
                        "Check server logs for startup errors "
                        "(likely missing MAPBOX_TOKEN or CSV file)."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        routing_svc = RouteConfig.routing_service
        fuel_index = RouteConfig.fuel_station_index
        optimizer = RouteConfig.fuel_optimizer

        try:
            # --------------------------------------------------------------
            # 3. Fetch route — ONE external API call
            # --------------------------------------------------------------
            route_result = routing_svc.get_route(start, end)

            # --------------------------------------------------------------
            # 4. Find fuel stations near the route — pure in-memory KDTree
            # --------------------------------------------------------------
            from django.conf import settings

            nearby = fuel_index.find_near_route(
                route_coords=route_result.coords,
                route_cum_miles=route_result.cum_miles,
                max_off_route_miles=settings.MAX_OFF_ROUTE_MILES,
            )

            logger.info(
                "Found %d candidate fuel stations near route (%.1f mi, %d coords).",
                len(nearby),
                route_result.total_miles,
                len(route_result.coords),
            )

            # --------------------------------------------------------------
            # 5. Optimize fuel stops — pure in-memory greedy algorithm
            # --------------------------------------------------------------
            opt_result = optimizer.optimize(
                candidate_stations=nearby,
                total_route_miles=route_result.total_miles,
            )

        except ValueError as exc:
            # Geocoding failures, unresolvable locations, etc.
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        except RouteOptimizationError as exc:
            # Algorithm couldn't find a feasible path (no stations in range).
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
                {"error": "Internal server error. See server logs for details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ------------------------------------------------------------------
        # 6. Serialize response
        # ------------------------------------------------------------------
        response_data = {
            "start":       start,
            "end":         end,
            "total_miles": round(route_result.total_miles, 1),
            "duration_hours": round(route_result.duration_sec / 3600, 2),
            # Return every 5th coordinate to keep payload size manageable
            # (full polyline can be thousands of points).
            # Clients that need the complete geometry should decode the
            # Mapbox polyline themselves.
            "route": [
                {"lat": lat, "lon": lon}
                for lat, lon in route_result.coords[::5]
            ],
            "fuel_stops": [
                {
                    "station_id":       stop.station_id,
                    "name":             stop.name,
                    "city":             stop.city,
                    "state":            stop.state,
                    "lat":              stop.lat,
                    "lon":              stop.lon,
                    "route_mile":       stop.route_mile,
                    "off_route_miles":  stop.off_route_miles,
                    "gallons_added":    stop.gallons_added,
                    "price_per_gallon": stop.price_per_gallon,
                    "stop_cost":        stop.stop_cost,
                }
                for stop in opt_result.fuel_stops
            ],
            "total_fuel_cost": opt_result.total_fuel_cost,
            "total_gallons":   opt_result.total_gallons,
        }

        out_serializer = RouteResponseSerializer(data=response_data)
        out_serializer.is_valid(raise_exception=True)
        return Response(out_serializer.validated_data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _services_ready() -> bool:
        return (
            RouteConfig.routing_service is not None
            and RouteConfig.fuel_station_index is not None
            and RouteConfig.fuel_optimizer is not None
        )
