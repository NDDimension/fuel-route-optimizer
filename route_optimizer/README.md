# Route Optimizer API

A high-performance Django REST API that computes the **cheapest fuel-stop plan**
for a road trip across the USA.

---

## Architecture Overview

```
POST /route/
     │
     ▼
RouteView
     │
     ├─ RoutingService.get_route()          ← 1 Mapbox Directions API call
     │       └─ GeocodingService (cached)  ← geocodes start/end location text
     │
     ├─ FuelStationIndex.find_near_route()  ← KDTree query, zero I/O
     │       (loaded once at startup)
     │
     └─ FuelOptimizer.optimize()            ← greedy look-ahead, zero I/O
```

**Single external API call per request** — the Mapbox Directions API is called
once with `overview=full` to get the complete route geometry. Everything else
is in-memory.

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Web framework | Django 5 + DRF | Standard, battle-tested |
| Routing API | Mapbox Directions | Single call, full polyline |
| Geocoding | Mapbox Forward Geocoding | Same token, cached to SQLite |
| Polyline decode | `polyline` library | Pure Python, no binary deps |
| Spatial index | `scipy.spatial.KDTree` | O(log n) nearest-neighbour |
| Coordinate math | `numpy` + `math` | No external geo libs needed |

---

## Fuel Optimization Algorithm

**Greedy with look-ahead** (O(S) single pass, where S = candidate stations):

1. Start with a full tank (50 gal = 500 miles range).
2. At each step, find all stations reachable with current fuel.
3. Drive to the **cheapest** reachable station.
4. At that station, decide how much to fill:
   - If a **cheaper** station exists within one full-tank range ahead → fill
     only enough to reach it (plus 5 % safety buffer).
   - Otherwise → fill the tank completely (this is the best price for
     the next 500 miles, so maximise cheap fuel).
5. Repeat until the destination is reachable on current fuel.

This produces near-optimal solutions and runs in microseconds.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A [Mapbox account](https://account.mapbox.com/) with a public access token

### 2. Install

```bash
git clone <repo>
cd route_optimizer

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set MAPBOX_TOKEN=pk.your_token_here
```

### 4. Pre-warm the geocode cache (recommended, one-time)

On first run, all ~4 200 unique city+state pairs from the CSV need to be
geocoded. This takes **60–120 seconds** with a fast connection. The results
are cached in `geocode_cache.db` — subsequent starts are instant.

```bash
python manage.py preload_fuel_data
```

### 5. Start the server

```bash
python manage.py runserver
```

---

## API Reference

### `POST /route/`

#### Request

```json
{
    "start": "New York, NY",
    "end":   "Los Angeles, CA"
}
```

Both fields accept any location string that Mapbox can geocode — city names,
street addresses, ZIP codes, etc.

#### Response

```json
{
    "start":          "New York, NY",
    "end":            "Los Angeles, CA",
    "total_miles":    2789.4,
    "duration_hours": 40.1,
    "route": [
        {"lat": 40.7128, "lon": -74.006},
        {"lat": 40.6892, "lon": -74.044},
        "..."
    ],
    "fuel_stops": [
        {
            "station_id":       "7",
            "name":             "WOODSHED OF BIG CABIN",
            "city":             "Big Cabin",
            "state":            "OK",
            "lat":              36.54,
            "lon":              -95.07,
            "route_mile":       1423.2,
            "off_route_miles":  0.8,
            "gallons_added":    38.2,
            "price_per_gallon": 3.007,
            "stop_cost":        114.87
        }
    ],
    "total_fuel_cost": 843.21,
    "total_gallons":   284.1
}
```

#### Error responses

| Status | Cause |
|--------|-------|
| 400 | Invalid input or unresolvable location |
| 422 | No fuel stations found within range of the route |
| 502 | Mapbox API returned an error |
| 503 | Server not fully initialised (check logs) |

#### Example with curl

```bash
curl -X POST http://localhost:8000/route/ \
     -H "Content-Type: application/json" \
     -d '{"start": "Chicago, IL", "end": "Dallas, TX"}'
```

---

## Configuration Reference

All settings are environment variables (set in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MAPBOX_TOKEN` | *(required)* | Mapbox public access token |
| `FUEL_CSV_PATH` | `data/fuel_prices.csv` | Path to fuel-price CSV |
| `GEOCODE_CACHE_PATH` | `geocode_cache.db` | SQLite geocode cache file |
| `MAX_OFF_ROUTE_MILES` | `5.0` | Max distance from route to include a station |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DJANGO_SECRET_KEY` | *(change me)* | Django secret key |

---

## Performance Notes

| Operation | Complexity | Typical time |
|-----------|-----------|--------------|
| Startup (warm cache) | O(N log N) KDTree build | ~2 s |
| Startup (cold cache) | O(C × geocode_rtt) | 60–120 s |
| Route fetch (Mapbox) | 1 HTTP call | ~300 ms |
| Station projection (KDTree) | O((S+R) log R) | < 10 ms |
| Fuel optimization | O(S) | < 1 ms |

S = stations along route, R = route coordinates, C = unique city+state pairs.

---

## Project Structure

```
route_optimizer/
├── manage.py
├── requirements.txt
├── .env.example
├── data/
│   └── fuel_prices.csv
├── config/
│   ├── settings.py          # All configuration
│   ├── urls.py
│   └── wsgi.py
└── route/
    ├── apps.py              # Startup: loads + indexes all services
    ├── views.py             # POST /route/ — orchestration only
    ├── serializers.py       # Input validation + output shaping
    ├── urls.py
    ├── management/
    │   └── commands/
    │       └── preload_fuel_data.py   # One-time geocode warmup
    └── services/
        ├── geocoding.py     # Mapbox geocoding + SQLite cache
        ├── routing.py       # Mapbox Directions API + polyline decode
        ├── fuel.py          # CSV loader + KDTree spatial index
        └── optimizer.py     # Greedy look-ahead algorithm
```
