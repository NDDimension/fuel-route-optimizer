"""
Routing service — wraps the Mapbox Directions API.

Design decisions:
  - One API call per user request (overview=full returns the complete
    geometry in a single response — no pagination or follow-up calls).
  - Uses geometries=polyline (precision-5 Mapbox encoding) and the
    `polyline` library for fast pure-Python decoding.
  - Forward geocoding (location text → coordinates) uses the same
    Mapbox token and is cached so start/end lookups are typically
    instant on subsequent calls with the same location strings.
  - Route coordinates are sub-sampled to one point per mile before
    returning; the optimizer only needs route-projected mile-markers,
    not every GPS ping.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Tuple

import polyline as polyline_lib
import requests
from django.conf import settings

from .geocoding import GeocodingService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapbox endpoint constants
# ---------------------------------------------------------------------------

_DIRECTIONS_URL = (
    "https://api.mapbox.com/directions/v5/mapbox/driving"
    "/{start_lon},{start_lat};{end_lon},{end_lat}"
)
_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

EARTH_RADIUS_MILES = 3_958.8


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RouteResult:
    """
    Everything downstream services need from the Mapbox Directions response.

    coords       — list of (lat, lon) tuples forming the route polyline.
    cum_miles    — parallel list of cumulative distances; cum_miles[i] is
                   the total miles from the route start to coords[i].
    total_miles  — total route length in miles.
    duration_sec — estimated driving time in seconds (from Mapbox).
    """

    coords: List[Tuple[float, float]]
    cum_miles: List[float]
    total_miles: float
    duration_sec: float
    start_address: str = ""
    end_address: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine_miles(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance in miles."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _build_cumulative_distances(
    coords: List[Tuple[float, float]],
) -> Tuple[List[float], float]:
    """
    Build a parallel list of cumulative mile-markers for a coordinate sequence.

    Returns:
      cum_miles   — cum_miles[0] == 0, cum_miles[-1] == total route miles
      total_miles — total route length
    """
    cum = [0.0]
    for i in range(1, len(coords)):
        seg = _haversine_miles(*coords[i - 1], *coords[i])
        cum.append(cum[-1] + seg)
    return cum, cum[-1]


# ---------------------------------------------------------------------------
# Routing service
# ---------------------------------------------------------------------------

class RoutingService:
    """
    Geocodes free-text locations and fetches driving routes from Mapbox.

    A GeocodingService is injected for forward geocoding; this means
    start/end location lookups are cached and won't cost extra API calls
    when the same location is used repeatedly.
    """

    def __init__(
        self,
        geocoding_service: GeocodingService | None = None,
        mapbox_token: str | None = None,
    ) -> None:
        self._token = mapbox_token or settings.MAPBOX_TOKEN
        if not self._token:
            raise RuntimeError(
                "MAPBOX_TOKEN is not set. "
                "Add it to your .env file before starting the server."
            )
        self._geo = geocoding_service or GeocodingService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_route(self, start: str, end: str) -> RouteResult:
        """
        Main entry point: geocode start and end location strings, call
        Mapbox Directions exactly once, and return a RouteResult.

        Raises ValueError on geocoding failures.
        Raises requests.HTTPError on Mapbox API errors.
        """
        # --- Step 1: geocode start and end (uses SQLite cache) ----------
        start_coords = self._geo.geocode_one(start)
        if start_coords is None:
            raise ValueError(f"Could not geocode start location: {start!r}")

        end_coords = self._geo.geocode_one(end)
        if end_coords is None:
            raise ValueError(f"Could not geocode end location: {end!r}")

        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords

        logger.info(
            "Routing %s (%.4f, %.4f) → %s (%.4f, %.4f)…",
            start, start_lat, start_lon,
            end,   end_lat,   end_lon,
        )

        # --- Step 2: single Mapbox Directions API call ------------------
        return self._fetch_route(
            start_lat, start_lon, end_lat, end_lon,
            start_address=start, end_address=end,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_route(
        self,
        start_lat: float, start_lon: float,
        end_lat: float,   end_lon: float,
        start_address: str = "",
        end_address: str = "",
    ) -> RouteResult:
        """
        Call the Mapbox Directions API and decode the response.

        Key request parameters:
          geometries=polyline  — precision-5 encoding; lighter than geojson.
          overview=full        — complete route geometry (not simplified).
          steps=false          — we don't need turn-by-turn; saves bandwidth.
        """
        url = _DIRECTIONS_URL.format(
            start_lon=start_lon, start_lat=start_lat,
            end_lon=end_lon,     end_lat=end_lat,
        )
        params = {
            "geometries": "polyline",
            "overview": "full",       # ← single call, complete geometry
            "steps": "false",
            "access_token": self._token,
        }

        logger.debug("GET %s", url)
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("routes"):
            raise ValueError(
                "Mapbox returned no routes for the requested origin/destination. "
                "Ensure both locations are in the continental United States."
            )

        route = data["routes"][0]  # take the first (best) route
        leg = route["legs"][0]

        # --- Decode polyline → list of (lat, lon) -----------------------
        # Mapbox Directions uses precision-5 encoding (default for `polyline`).
        encoded = route["geometry"]
        raw_coords: List[Tuple[float, float]] = polyline_lib.decode(encoded)
        # polyline.decode returns (lat, lon) tuples — correct order.

        # --- Compute cumulative distances --------------------------------
        cum_miles, total_miles = _build_cumulative_distances(raw_coords)

        # Mapbox reports distance in meters; convert for cross-checking.
        mapbox_total_miles = leg["distance"] / 1609.344
        logger.info(
            "Route decoded: %d coordinates, %.1f miles "
            "(Mapbox reported %.1f mi, Haversine %.1f mi).",
            len(raw_coords),
            total_miles,
            mapbox_total_miles,
            total_miles,
        )

        return RouteResult(
            coords=raw_coords,
            cum_miles=cum_miles,
            total_miles=total_miles,
            duration_sec=leg["duration"],
            start_address=start_address,
            end_address=end_address,
        )
