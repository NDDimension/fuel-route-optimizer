"""
Geocoding service — converts (city, state) text queries to (lat, lon) coordinates.

Design decisions:
  - Mapbox Forward Geocoding API (same token as Directions API → no extra credentials).
  - SQLite cache stored on disk: zero network calls on warm restarts.
  - ThreadPoolExecutor for concurrent geocoding on first run.
  - Rate-limited to GEOCODING_MAX_WORKERS concurrent requests to stay under
    Mapbox free tier limit of 600 req/min.
  - Failed lookups are stored as NULL so we don't retry them forever.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Mapbox forward-geocoding endpoint.
_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"


class GeocodingService:
    """
    Thread-safe geocoding service with a persistent SQLite look-aside cache.

    Usage:
        svc = GeocodingService()
        coords = svc.geocode_batch(["Austin, TX", "Boise, ID"])
        # {"Austin, TX": (30.267, -97.743), "Boise, ID": (43.615, -116.202)}
    """

    def __init__(
        self,
        cache_path: Path | None = None,
        mapbox_token: str | None = None,
    ) -> None:
        self._token = mapbox_token or settings.MAPBOX_TOKEN
        self._cache_path = cache_path or settings.GEOCODE_CACHE_PATH
        self._conn = self._init_cache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def geocode_batch(
        self,
        queries: list[str],
        max_workers: int | None = None,
    ) -> Dict[str, Optional[Tuple[float, float]]]:
        """
        Geocode a list of query strings, returning a dict of
        {query: (lat, lon)} or {query: None} when lookup fails.

        Already-cached results are returned instantly; only cache misses
        trigger network requests.
        """
        workers = max_workers or settings.GEOCODING_MAX_WORKERS
        result: Dict[str, Optional[Tuple[float, float]]] = {}

        # --- Phase 1: load hits from cache ---------------------------------
        misses: list[str] = []
        for q in queries:
            cached = self._cache_get(q)
            if cached is not False:       # False means "not in cache at all"
                result[q] = cached        # None means "cached miss" — skip it
            else:
                misses.append(q)

        if not misses:
            return result

        logger.info(
            "Geocoding %d locations (%d already cached)…",
            len(misses),
            len(queries) - len(misses),
        )

        # --- Phase 2: fetch misses concurrently ----------------------------
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_query = {
                pool.submit(self._geocode_one, q): q for q in misses
            }
            completed = 0
            total = len(misses)
            for future in as_completed(future_to_query):
                q = future_to_query[future]
                try:
                    coords = future.result()
                except Exception as exc:
                    logger.warning("Geocoding failed for %r: %s", q, exc)
                    coords = None

                result[q] = coords
                self._cache_set(q, coords)

                completed += 1
                if completed % 100 == 0 or completed == total:
                    logger.info("  Geocoded %d / %d locations…", completed, total)

        return result

    def geocode_one(self, query: str) -> Optional[Tuple[float, float]]:
        """Geocode a single query, using cache."""
        cached = self._cache_get(query)
        if cached is not False:
            return cached
        coords = self._geocode_one(query)
        self._cache_set(query, coords)
        return coords

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _geocode_one(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Call the Mapbox Forward Geocoding API for a single query.
        Retries up to GEOCODING_RETRY_ATTEMPTS times on transient errors.
        """
        url = _GEOCODE_URL.format(query=quote(query))
        params = {
            "types": "place,locality,neighborhood",
            "country": "US",
            "limit": 1,
            "access_token": self._token,
        }

        for attempt in range(1, settings.GEOCODING_RETRY_ATTEMPTS + 1):
            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                if not features:
                    logger.debug("No geocoding result for %r", query)
                    return None
                lon, lat = features[0]["geometry"]["coordinates"]
                return float(lat), float(lon)
            except requests.RequestException as exc:
                if attempt == settings.GEOCODING_RETRY_ATTEMPTS:
                    logger.warning("Geocoding gave up on %r after %d attempts: %s", query, attempt, exc)
                    return None
                wait = 2 ** attempt  # exponential back-off: 2s, 4s
                logger.debug("Retrying %r in %ds (attempt %d)…", query, wait, attempt)
                time.sleep(wait)

        return None  # unreachable but keeps type checker happy

    # ------------------------------------------------------------------
    # SQLite cache helpers
    # ------------------------------------------------------------------

    def _init_cache(self) -> sqlite3.Connection:
        """
        Open (or create) the SQLite cache database.
        The table stores NULL lat/lon for confirmed misses so we
        don't waste API quota re-querying them.
        """
        conn = sqlite3.connect(str(self._cache_path), check_same_thread=False)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS geocode_cache (
                query TEXT PRIMARY KEY,
                lat   REAL,
                lon   REAL
            )
            """
        )
        conn.commit()
        return conn

    def _cache_get(self, query: str) -> Optional[Tuple[float, float]] | bool:
        """
        Return:
          (lat, lon) if found and successful,
          None       if found but geocoding previously failed,
          False      if not in cache at all.
        """
        row = self._conn.execute(
            "SELECT lat, lon FROM geocode_cache WHERE query = ?", (query,)
        ).fetchone()
        if row is None:
            return False                        # cache miss
        lat, lon = row
        if lat is None:
            return None                         # known failure
        return float(lat), float(lon)

    def _cache_set(
        self, query: str, coords: Optional[Tuple[float, float]]
    ) -> None:
        lat = coords[0] if coords else None
        lon = coords[1] if coords else None
        self._conn.execute(
            "INSERT OR REPLACE INTO geocode_cache (query, lat, lon) VALUES (?, ?, ?)",
            (query, lat, lon),
        )
        self._conn.commit()
