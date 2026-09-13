"""Shared routing configuration."""

import os

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
#OSRM_URL = os.getenv("OSRM_URL", "http://openstreetmap.de")
OSRM_TIMEOUT_SECONDS = float(os.getenv("OSRM_TIMEOUT_SECONDS", "20"))
DEFAULT_MOTORCYCLE_EMISSION_FACTOR = 0.06  # kg CO2/km
BLOCKED_EDGE_PENALTY = float("inf")
