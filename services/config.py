"""Shared routing configuration."""

import os

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
OSRM_TIMEOUT_SECONDS = float(os.getenv("OSRM_TIMEOUT_SECONDS", "20"))

DEFAULT_MOTORCYCLE_EMISSION_FACTOR = 0.06
BLOCKED_EDGE_PENALTY = float("inf")

# Controlled demo state: after one completed leg, Traffic is placed on
# the next leg. With urgent O001 this is O001 -> O002.
COMPLETED_LEGS_BEFORE_INCIDENT = int(
    os.getenv("COMPLETED_LEGS_BEFORE_INCIDENT", "1")
)

# Weather incident is placed around the middle of the route.
WEATHER_POSITION_RATIO = float(
    os.getenv("WEATHER_POSITION_RATIO", "0.5")
)

# Demo visualization thresholds; not real-world safety standards.
TRAFFIC_CLEARANCE_M = float(os.getenv("TRAFFIC_CLEARANCE_M", "150"))
WEATHER_CLEARANCE_M = float(os.getenv("WEATHER_CLEARANCE_M", "400"))
