"""
Django settings for route_optimizer.

Environment variables are loaded from a .env file via python-dotenv.
All sensitive values (API keys, secrets) must come from the environment —
never hardcode them here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root (BASE_DIR) so local dev works without
# having to export variables in the shell.
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-default-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

def split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


render_external_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
configured_allowed_hosts = split_env_list(os.environ.get("ALLOWED_HOSTS", ""))

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = configured_allowed_hosts or [
        render_external_hostname,
        "localhost",
        "127.0.0.1",
    ]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    # Our app — AppConfig.ready() loads + indexes fuel data at startup.
    "route.apps.RouteConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = split_env_list(os.environ.get("CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOWED_ORIGIN_REGEXES = split_env_list(os.environ.get("CORS_ALLOWED_ORIGIN_REGEXES", ""))

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# No database needed — all state lives in memory + the geocode SQLite cache.
DATABASES = {}

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Return 400 for validation errors, 500 for unexpected exceptions.
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# ---------------------------------------------------------------------------
# Project-specific settings
# ---------------------------------------------------------------------------

# Mapbox access token — required for both geocoding and directions.
MAPBOX_TOKEN: str = os.environ.get("MAPBOX_TOKEN", "")

# Absolute path to the fuel-price CSV file.
FUEL_CSV_PATH: Path = BASE_DIR / os.environ.get("FUEL_CSV_PATH", "data/fuel_prices.csv")

# SQLite file that caches (city, state) → (lat, lon) lookups.
GEOCODE_CACHE_PATH: Path = BASE_DIR / os.environ.get("GEOCODE_CACHE_PATH", "geocode_cache.db")

# Vehicle constants — these match the problem specification.
VEHICLE_MPG: float = 10.0          # miles per gallon
VEHICLE_MAX_RANGE_MILES: float = 500.0  # maximum range on a full tank
VEHICLE_TANK_GALLONS: float = VEHICLE_MAX_RANGE_MILES / VEHICLE_MPG  # 50 gal

# Spatial search parameters.
MAX_OFF_ROUTE_MILES: float = float(os.environ.get("MAX_OFF_ROUTE_MILES", "5.0"))

# Geocoding concurrency — stay well under Mapbox free-tier 600 req/min limit.
GEOCODING_MAX_WORKERS: int = 8
GEOCODING_RETRY_ATTEMPTS: int = 3
