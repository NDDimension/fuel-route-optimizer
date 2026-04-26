"""
Fuel-stop optimization service.

Algorithm: Greedy with look-ahead (a well-known approximation for the
"cheapest refueling on a fixed route" problem).

Core intuition:
  - At each potential stop, fill up COMPLETELY if it is the cheapest
    station within a full-tank's range ahead of us (no point in leaving
    cheap fuel behind).
  - Otherwise, fill only ENOUGH to reach the next cheaper station — we
    don't want to carry expensive fuel past a bargain stop.

This single-pass O(S) algorithm (where S is candidate stations along the
route) produces near-optimal solutions and is trivially fast.

Constraints from the problem spec:
  - Max range:      500 miles per full tank
  - Fuel efficiency: 10 miles per gallon  →  tank capacity = 50 gallons
  - Start condition: full tank (common assumption for fleet routing)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FuelStop:
    """A single refuelling event along the optimized route."""

    station_id: str
    name: str
    city: str
    state: str
    lat: float
    lon: float
    route_mile: float          # mile-marker along the route where stop occurs
    off_route_miles: float     # how far off the highway this station sits
    gallons_added: float       # gallons purchased at this stop
    price_per_gallon: float    # retail price at the pump
    stop_cost: float           # gallons_added × price_per_gallon


@dataclass
class OptimizationResult:
    """Complete output of the fuel optimization pass."""

    fuel_stops: List[FuelStop]
    total_fuel_cost: float     # sum of all stop_cost values
    total_gallons: float       # sum of all gallons_added values
    total_route_miles: float


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RouteOptimizationError(Exception):
    """Raised when no feasible solution can be found (e.g. no stations)."""


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

class FuelOptimizer:
    """
    Stateless optimizer: call optimize() with route data and nearby stations.

    Parameters are taken from Django settings so they're configurable
    without code changes.
    """

    def __init__(
        self,
        mpg: float | None = None,
        tank_gallons: float | None = None,
        max_range_miles: float | None = None,
    ) -> None:
        self.mpg = mpg or settings.VEHICLE_MPG                      # 10 mi/gal
        self.tank_gallons = tank_gallons or settings.VEHICLE_TANK_GALLONS  # 50 gal
        self.max_range = max_range_miles or settings.VEHICLE_MAX_RANGE_MILES  # 500 mi

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        candidate_stations: list[dict],  # output of FuelStationIndex.find_near_route()
        total_route_miles: float,
    ) -> OptimizationResult:
        """
        Compute the cheapest set of fuel stops for a given route.

        candidate_stations: list of dicts with keys:
            station        — FuelStation
            route_mile     — float, position along the route
            off_route_miles — float

        Returns an OptimizationResult with the ordered list of stops
        and the total cost.
        """
        if not candidate_stations:
            logger.warning(
                "No fuel stations found near route. "
                "Consider increasing MAX_OFF_ROUTE_MILES."
            )

        # Sort stations by their position along the route.
        sorted_stations = sorted(candidate_stations, key=lambda s: s["route_mile"])

        stops, total_cost, total_gallons = self._greedy_optimize(
            sorted_stations, total_route_miles
        )

        logger.info(
            "Optimization complete: %d stops, $%.2f total, %.1f gal total.",
            len(stops), total_cost, total_gallons,
        )

        return OptimizationResult(
            fuel_stops=stops,
            total_fuel_cost=round(total_cost, 2),
            total_gallons=round(total_gallons, 2),
            total_route_miles=round(total_route_miles, 2),
        )

    # ------------------------------------------------------------------
    # Core algorithm
    # ------------------------------------------------------------------

    def _greedy_optimize(
        self,
        sorted_stations: list[dict],
        total_miles: float,
    ) -> tuple[list[FuelStop], float, float]:
        """
        Single-pass greedy algorithm.

        State variables:
          pos   — current mile-marker along the route
          fuel  — current fuel level in gallons

        At each iteration we decide:
          1. Which station to stop at next.
          2. How many gallons to add there.
        """
        pos: float = 0.0
        fuel: float = self.tank_gallons     # start with a full tank
        stops: list[FuelStop] = []
        total_cost: float = 0.0
        total_gallons: float = 0.0

        while True:
            remaining_range = fuel * self.mpg

            # ---- Are we done? ------------------------------------------
            if pos + remaining_range >= total_miles:
                break  # destination reachable on current tank

            # ---- Find reachable stations --------------------------------
            reachable = [
                s for s in sorted_stations
                if pos < s["route_mile"] <= pos + remaining_range
            ]

            if not reachable:
                raise RouteOptimizationError(
                    f"No fuel stations reachable from mile {pos:.1f} "
                    f"(remaining range: {remaining_range:.1f} mi). "
                    "Try increasing MAX_OFF_ROUTE_MILES or check route coverage."
                )

            # ---- Pick the cheapest reachable station -------------------
            # This is the "look-behind" part: among stations we can actually
            # get to, choose the one with the lowest price.
            best = min(reachable, key=lambda s: s["station"].price)

            # ---- Drive to that station ---------------------------------
            miles_driven = best["route_mile"] - pos
            fuel -= miles_driven / self.mpg
            pos = best["route_mile"]

            # ---- Decide how much fuel to add (look-ahead) --------------
            fill_amount = self._compute_fill_amount(
                pos=pos,
                current_fuel=fuel,
                current_price=best["station"].price,
                sorted_stations=sorted_stations,
                total_miles=total_miles,
            )

            if fill_amount <= 0.001:
                # This stop is unnecessary (edge case: we arrived here with
                # enough fuel already and there's a cheaper option ahead).
                # Skip it to avoid recording a zero-gallon stop.
                continue

            cost = fill_amount * best["station"].price
            total_cost += cost
            total_gallons += fill_amount
            fuel += fill_amount

            stops.append(
                FuelStop(
                    station_id=best["station"].station_id,
                    name=best["station"].name,
                    city=best["station"].city,
                    state=best["station"].state,
                    lat=best["station"].lat,
                    lon=best["station"].lon,
                    route_mile=round(pos, 1),
                    off_route_miles=best["off_route_miles"],
                    gallons_added=round(fill_amount, 3),
                    price_per_gallon=round(best["station"].price, 4),
                    stop_cost=round(cost, 2),
                )
            )

        return stops, total_cost, total_gallons

    def _compute_fill_amount(
        self,
        pos: float,
        current_fuel: float,
        current_price: float,
        sorted_stations: list[dict],
        total_miles: float,
    ) -> float:
        """
        Determine how many gallons to add at the current stop.

        Rules (greedy look-ahead):
          A) Find all stations within a full-tank's range ahead of here.
          B) If any of those stations is CHEAPER than the current station:
               → Fill only enough to reach the nearest cheaper one,
                 plus a small safety buffer.
          C) Otherwise (this is the cheapest in range):
               → Fill the tank completely.

        Edge case: if filling to reach the destination (no future stops
        needed), fill exactly what's required to make it there.
        """
        full_range_ahead = pos + self.max_range

        # Stations ahead within one full tank.
        ahead_in_range = [
            s for s in sorted_stations
            if pos < s["route_mile"] <= full_range_ahead
        ]

        # Cheaper stations within range.
        cheaper_ahead = [
            s for s in ahead_in_range
            if s["station"].price < current_price
        ]

        if cheaper_ahead:
            # Fill just enough to reach the nearest cheaper station.
            nearest_cheaper = min(cheaper_ahead, key=lambda s: s["route_mile"])
            miles_to_cheaper = nearest_cheaper["route_mile"] - pos
            fuel_to_reach = miles_to_cheaper / self.mpg
            # Add a 5 % safety buffer so we don't arrive on fumes.
            needed = fuel_to_reach * 1.05
            fill = max(0.0, needed - current_fuel)
        else:
            # No cheaper option ahead — fill the tank completely.
            fill = self.tank_gallons - current_fuel

        # Never exceed tank capacity.
        fill = min(fill, self.tank_gallons - current_fuel)
        return max(0.0, fill)
