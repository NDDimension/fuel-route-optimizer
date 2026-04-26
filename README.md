# RouteOpt

Fuel-aware route optimization for long-haul US trucking.

RouteOpt is a full-stack route planning application that helps drivers and fleet operators reduce fuel spend on cross-country trips. Given a start and destination, the system computes a driving route, identifies reachable stations along the path, and selects a cost-efficient fueling strategy based on route distance, station pricing, and vehicle range.

The repository includes:

- a production-quality React + TypeScript frontend with a dark-map command-center interface
- a Django REST API that computes optimized fuel stop plans
- deployment configuration for Render (backend) and Vercel (frontend)

## Highlights

- Fuel-optimized trip planning for long-haul US routes
- Interactive full-screen Mapbox experience with route line, custom markers, and stop popups
- Responsive sidebar-to-bottom-sheet layout for desktop and mobile
- Typed frontend and backend contracts
- Reducer-driven request lifecycle and resilient error handling
- Render + Vercel deployment setup included in the repo

## Product Experience

The frontend is designed as a logistics control surface rather than a demo dashboard.

- Drivers enter a start and destination
- The frontend requests an optimized route from the API
- The backend geocodes the locations, fetches a route from Mapbox, finds nearby candidate stations, and computes the best stop sequence
- The UI renders:
  - total trip fuel cost
  - route mileage and estimated duration
  - total gallons added
  - every planned fuel stop with price, gallons, and stop cost
- Selecting a stop in the list focuses the map and opens its popup
- Selecting a marker on the map scrolls the corresponding stop card into view

## Architecture

### Frontend

The frontend is built with:

- React 18
- TypeScript in strict mode
- Vite
- Tailwind CSS v3
- Framer Motion
- Mapbox GL JS via `react-map-gl`
- Lucide React

Key frontend responsibilities:

- collect trip input
- manage request state transitions
- render optimized route summaries
- visualize routes and fuel stops on an interactive map
- keep map movement and UI interactions in sync

### Backend

The backend is a Django + Django REST Framework service that exposes a single core optimization endpoint:

- `POST /route/`

It is responsible for:

- validating incoming route requests
- geocoding start and destination text
- fetching route geometry from Mapbox Directions
- locating nearby stations from the fuel price dataset
- running the fuel optimization algorithm
- returning a structured response to the frontend

### Optimization Flow

At a high level, a request follows this path:

```text
Frontend form submit
  -> POST /route/
  -> Validate request
  -> Geocode origin and destination
  -> Fetch route geometry from Mapbox
  -> Find nearby candidate stations
  -> Optimize fuel stops
  -> Return route summary + stop list + polyline coordinates
  -> Render map and sidebar UI
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + Vite |
| Frontend language | TypeScript |
| Styling | Tailwind CSS v3 |
| Animation | Framer Motion |
| Mapping | Mapbox GL JS + react-map-gl |
| Icons | Lucide React |
| Backend | Django 5 + DRF |
| Routing & geocoding | Mapbox APIs |
| Optimization data structures | NumPy + SciPy KDTree |
| Deployment | Vercel + Render |

## Repository Structure

```text
.
├── src/                         # React frontend
├── route_optimizer/             # Django backend
├── render.yaml                  # Render Blueprint for the backend
├── vercel.json                  # Vercel project configuration
├── DEPLOYMENT.md                # Platform-specific deployment notes
├── package.json                 # Frontend dependencies and scripts
└── README.md                    # Project overview
```

### Frontend Structure

```text
src/
├── App.tsx
├── api/
├── components/
│   ├── MapView/
│   ├── RouteForm/
│   ├── Sidebar/
│   └── UI/
├── hooks/
├── types/
└── utils/
```

### Backend Structure

```text
route_optimizer/
├── config/
├── data/
├── route/
│   ├── management/
│   └── services/
├── manage.py
└── requirements.txt
```

For a deeper backend-specific walkthrough, see [route_optimizer/README.md](./route_optimizer/README.md).

## Local Development

### Prerequisites

- Node.js 20+
- npm 10+
- Python 3.11+
- a Mapbox token

### 1. Clone the repository

```bash
git clone https://github.com/NDDimension/fuel-route-optimizer.git
cd fuel-route-optimizer
```

### 2. Configure the frontend

Create a root `.env` file:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_MAPBOX_TOKEN=pk.your_mapbox_public_token_here
```

Install frontend dependencies:

```bash
npm install
```

### 3. Configure the backend

Move into the Django app:

```bash
cd route_optimizer
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create `route_optimizer/.env`:

```bash
MAPBOX_TOKEN=pk.your_mapbox_public_token_here
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
FUEL_CSV_PATH=data/fuel_prices.csv
GEOCODE_CACHE_PATH=geocode_cache.db
MAX_OFF_ROUTE_MILES=5.0
```

### 4. Optional: pre-warm the fuel/geocode cache

This is recommended before the first run:

```bash
python manage.py preload_fuel_data
```

### 5. Start the backend

From `route_optimizer/`:

```bash
python manage.py runserver
```

The API will be available at:

```text
http://localhost:8000
```

### 6. Start the frontend

From the repository root in a separate terminal:

```bash
npm run dev
```

The app will usually be available at:

```text
http://localhost:5173
```

## Frontend Scripts

Run from the repository root:

```bash
npm run dev
npm run build
npm run preview
```

## API Overview

### `POST /route/`

Request body:

```json
{
  "start": "Chicago, IL",
  "end": "Dallas, TX"
}
```

Successful response:

```json
{
  "start": "Chicago, IL",
  "end": "Dallas, TX",
  "total_miles": 917.3,
  "duration_hours": 13.8,
  "route": [{ "lat": 41.878, "lon": -87.629 }],
  "fuel_stops": [
    {
      "station_id": "4821",
      "name": "PILOT TRAVEL CENTER #220",
      "city": "Springfield",
      "state": "IL",
      "lat": 39.801,
      "lon": -89.643,
      "route_mile": 201.4,
      "off_route_miles": 0.3,
      "gallons_added": 32.1,
      "price_per_gallon": 3.129,
      "stop_cost": 100.44
    }
  ],
  "total_fuel_cost": 284.73,
  "total_gallons": 91.7
}
```

Health endpoint:

```text
GET /health/
```

For complete backend details, request/response behavior, and algorithm notes, see [route_optimizer/README.md](./route_optimizer/README.md).

## Deployment

This repository is prepared for:

- Render for the Django API
- Vercel for the React frontend

Included deployment files:

- [render.yaml](./render.yaml)
- [vercel.json](./vercel.json)
- [DEPLOYMENT.md](./DEPLOYMENT.md)

### Render

The backend uses a Render Blueprint with:

- `gunicorn` as the production server
- a `/health/` health check
- a persistent disk mount for cache data
- environment-driven Django host and CORS configuration

### Vercel

The frontend uses standard Vite build output with:

- `npm install`
- `npm run build`
- `dist/` as the output directory

## Environment Variables

### Frontend

| Variable | Required | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | Yes | Base URL for the Django API |
| `VITE_MAPBOX_TOKEN` | Yes | Public Mapbox token for map rendering |

### Backend

| Variable | Required | Purpose |
|---|---|---|
| `MAPBOX_TOKEN` | Yes | Mapbox token for geocoding and routing |
| `DJANGO_SECRET_KEY` | Yes | Django application secret |
| `DJANGO_DEBUG` | Yes | Debug mode toggle |
| `ALLOWED_HOSTS` | Production | Allowed hostnames for Django |
| `CORS_ALLOWED_ORIGINS` | Production | Explicit frontend origins |
| `CORS_ALLOWED_ORIGIN_REGEXES` | Optional | Regex support for preview deployments |
| `FUEL_CSV_PATH` | No | Fuel price CSV path |
| `GEOCODE_CACHE_PATH` | No | SQLite cache path |
| `MAX_OFF_ROUTE_MILES` | No | Candidate station distance threshold |

## Engineering Notes

- The frontend keeps imperative map operations isolated inside a dedicated hook.
- The route API lifecycle is reducer-driven to keep success, loading, idle, and error states explicit.
- Large route geometry is not stored in React state unnecessarily.
- Fuel stop cards and map markers are memoized to avoid unnecessary rerenders.
- The backend performs only one upstream route fetch per request and keeps station lookup and optimization in memory.

## Data Source

The repository includes a fuel price dataset used by the backend optimizer to locate and compare candidate stops along a route.

## Future Improvements

- authentication and saved trips
- fleet-level route comparison
- cost sensitivity simulations by MPG and tank size
- historical fuel trend overlays
- exportable trip summaries for dispatch teams

## License

Copyright (c) 2026 **Dhanraj Sharma**. All rights reserved. This code is submitted as a technical assessment. Unauthorized copying, modification, or distribution is strictly prohibited.
