"""
DRF serializers for the POST /route/ endpoint.

Input  → RouteRequestSerializer  (validates start / end location strings)
Output → RouteResponseSerializer (shapes the API response from domain objects)

Using serializers rather than bare dicts keeps the contract explicit,
enables auto-generated API documentation (e.g. drf-spectacular), and
makes validation errors automatically 400 instead of 500.
"""

from rest_framework import serializers


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class RouteRequestSerializer(serializers.Serializer):
    """Validates the POST body for POST /route/."""

    start = serializers.CharField(
        max_length=256,
        help_text="Starting location, e.g. 'New York, NY' or '350 5th Ave, New York'",
    )
    end = serializers.CharField(
        max_length=256,
        help_text="Ending location, e.g. 'Los Angeles, CA'",
    )


# ---------------------------------------------------------------------------
# Response — nested serializers reflect the domain object structure
# ---------------------------------------------------------------------------

class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class FuelStopSerializer(serializers.Serializer):
    station_id      = serializers.CharField()
    name            = serializers.CharField()
    city            = serializers.CharField()
    state           = serializers.CharField()
    lat             = serializers.FloatField()
    lon             = serializers.FloatField()
    route_mile      = serializers.FloatField(help_text="Mile-marker along the route.")
    off_route_miles = serializers.FloatField(help_text="Distance from the nearest route point.")
    gallons_added   = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    stop_cost       = serializers.FloatField(help_text="Cost at this stop (USD).")


class RouteResponseSerializer(serializers.Serializer):
    """Shapes the complete API response."""

    start           = serializers.CharField()
    end             = serializers.CharField()
    total_miles     = serializers.FloatField()
    duration_hours  = serializers.FloatField(help_text="Estimated driving time in hours.")
    route           = CoordinateSerializer(many=True,
                        help_text="Ordered list of (lat, lon) coordinates along the route.")
    fuel_stops      = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField(help_text="Total fuel cost in USD.")
    total_gallons   = serializers.FloatField(help_text="Total gallons purchased.")
