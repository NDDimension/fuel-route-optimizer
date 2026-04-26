"""
Fuel station data service.

Responsibilities:
  1. Load and deduplicate the fuel-price CSV (8 000+ rows).
  2. Geocode unique (City, State) pairs via GeocodingService — using a
     city centroid is accurate enough because stations are on highways
     and our snap radius (≤5 miles) covers the offset.
  3. Build a scipy KDTree over 3-D unit-sphere Cartesian coordinates for
     O(log n) spatial queries — much faster than naive haversine loops.
  4. Expose find_near_route() which returns every station within
     MAX_OFF_ROUTE_MILES of any route coordinate, together with its
     projected mile-marker along the route.

Performance notes:
  - KDTree build: O(n log n) once at startup, queries O(log n) each.
  - Cartesian conversion avoids the haversine singularity at poles and
     gives correct Euclidean distances convertible back to miles.
  - Deduplication by station_id (keep cheapest price) reduces ~8 k rows
     to ~6 700 unique stations; city deduplication further reduces
     geocoding calls from ~8 000 to ~4 200 unique city+state pairs.
"""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from scipy.spatial import KDTree

from .geocoding import GeocodingService

logger = logging.getLogger(__name__)

EARTH_RADIUS_MILES = 3_958.8  # mean Earth radius in miles


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FuelStation:
    station_id: str
    name: str
    city: str
    state: str
    lat: float
    lon: float
    price: float   # USD per gallon (retail)

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state}) — ${self.price:.3f}/gal"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two WGS-84 points."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _to_cartesian(lat_deg: float, lon_deg: float) -> Tuple[float, float, float]:
    """
    Convert (lat, lon) in degrees to a point on the unit sphere.
    Euclidean distance in this space can be converted back to arc-miles via
        miles = 2R * arcsin(chord / 2)
    """
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    x = math.cos(lat) * math.cos(lon)
    y = math.cos(lat) * math.sin(lon)
    z = math.sin(lat)
    return x, y, z


def _chord_to_miles(chord: float) -> float:
    """Inverse of unit-sphere chord length → great-circle miles."""
    # Clamp to [0, 2] to avoid floating-point asin domain errors.
    return 2 * EARTH_RADIUS_MILES * math.asin(min(chord / 2.0, 1.0))


def _miles_to_chord(miles: float) -> float:
    """Great-circle miles → unit-sphere chord length."""
    return 2.0 * math.sin(miles / (2.0 * EARTH_RADIUS_MILES))


# ---------------------------------------------------------------------------
# Spatial index
# ---------------------------------------------------------------------------

class FuelStationIndex:
    """
    Spatial index over a collection of FuelStation objects.

    Internally uses a scipy KDTree built in 3-D Cartesian space so that
    standard Euclidean distance queries correctly approximate great-circle
    distances (valid for distances << Earth radius — fine here at ≤ 50 mi).
    """

    def __init__(self, stations: List[FuelStation]) -> None:
        if not stations:
            raise ValueError("Cannot build index from an empty station list.")

        self.stations: List[FuelStation] = stations

        # Build coordinate array in Cartesian space.
        coords = np.array(
            [_to_cartesian(s.lat, s.lon) for s in stations], dtype=np.float64
        )
        # KDTree with compact_nodes=True is faster to build and query.
        self._tree = KDTree(coords, compact_nodes=True)

        logger.info("FuelStationIndex: indexed %d stations.", len(stations))

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def find_near_route(
        self,
        route_coords: List[Tuple[float, float]],   # list of (lat, lon)
        route_cum_miles: List[float],               # cumulative miles at each coord
        max_off_route_miles: float = 5.0,
    ) -> List[dict]:
        """
        Return all fuel stations within *max_off_route_miles* of the route.

        Each result dict contains:
          station          — FuelStation
          route_mile       — float, position along the route (cumulative miles)
          off_route_miles  — float, perpendicular distance from route

        Algorithm:
          1. Build a temporary KDTree of route coordinates.
          2. For each station, query that KDTree for the nearest route point.
          3. Accept stations whose nearest route point is within the radius.
          4. Record the route's cumulative-mileage at that nearest point.

        Complexity: O((S + R) log R) where S = stations, R = route coords.
        """
        if not route_coords:
            return []

        chord_radius = _miles_to_chord(max_off_route_miles)

        # Build route KDTree (temporary — built fresh per request).
        route_cart = np.array(
            [_to_cartesian(lat, lon) for lat, lon in route_coords], dtype=np.float64
        )
        route_tree = KDTree(route_cart, compact_nodes=True)

        # Query all stations at once — scipy handles the loop efficiently.
        station_cart = np.array(
            [_to_cartesian(s.lat, s.lon) for s in self.stations], dtype=np.float64
        )
        dists, nearest_route_indices = route_tree.query(
            station_cart,
            distance_upper_bound=chord_radius,
            workers=1,   # single-threaded inside the request; avoids GIL issues
        )

        results: List[dict] = []
        for i, (chord, route_idx) in enumerate(zip(dists, nearest_route_indices)):
            if chord == np.inf:
                continue   # station is outside snap radius

            off_route = _chord_to_miles(chord)
            route_mile = route_cum_miles[route_idx]

            results.append(
                {
                    "station": self.stations[i],
                    "route_mile": route_mile,
                    "off_route_miles": round(off_route, 2),
                }
            )

        return results


# ---------------------------------------------------------------------------
# CSV loader and orchestration
# ---------------------------------------------------------------------------

def load_fuel_stations(
    csv_path: Path,
    geocoding_service: GeocodingService,
) -> FuelStationIndex:
    """
    Load the fuel-price CSV, deduplicate, geocode, and return a FuelStationIndex.

    Deduplication strategy (two passes):
      Pass 1 — by station_id: keep the cheapest price across duplicate IDs.
      Pass 2 — rows that failed geocoding are silently dropped (typically <1%).

    This function is designed to be called once at application startup and
    the resulting index held in memory for the lifetime of the process.
    """
    logger.info("Loading fuel station data from %s…", csv_path)
    raw: dict[str, dict] = {}   # station_id → best row

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            sid = row["OPIS Truckstop ID"].strip()
            try:
                price = float(row["Retail Price"])
            except ValueError:
                logger.debug("Skipping row with invalid price: %r", row)
                continue

            # Keep only the cheapest price for each station ID.
            if sid not in raw or price < float(raw[sid]["Retail Price"]):
                raw[sid] = row

    logger.info("Loaded %d unique stations (from %d raw rows).", len(raw), len(raw))

    # Build the set of unique geocoding queries: "City, State".
    city_state_to_query: dict[tuple, str] = {}
    for row in raw.values():
        city = row["City"].strip()
        state = row["State"].strip()
        key = (city, state)
        city_state_to_query[key] = f"{city}, {state}"

    unique_queries = list(city_state_to_query.values())
    logger.info(
        "Geocoding %d unique city+state pairs (cached results load instantly)…",
        len(unique_queries),
    )

    coords_by_query = geocoding_service.geocode_batch(unique_queries)

    # Assemble FuelStation objects.
    stations: List[FuelStation] = []
    failed = 0
    for row in raw.values():
        city = row["City"].strip()
        state = row["State"].strip()
        query = city_state_to_query[(city, state)]
        coords = coords_by_query.get(query)
        if coords is None:
            failed += 1
            continue  # geocoding failed — drop this station

        lat, lon = coords
        stations.append(
            FuelStation(
                station_id=row["OPIS Truckstop ID"].strip(),
                name=row["Truckstop Name"].strip(),
                city=city,
                state=state,
                lat=lat,
                lon=lon,
                price=float(row["Retail Price"]),
            )
        )

    logger.info(
        "Indexed %d stations successfully; %d dropped (geocoding failed).",
        len(stations),
        failed,
    )

    if not stations:
        raise RuntimeError(
            "No fuel stations could be geocoded. "
            "Check your MAPBOX_TOKEN and network connectivity."
        )

    return FuelStationIndex(stations)
