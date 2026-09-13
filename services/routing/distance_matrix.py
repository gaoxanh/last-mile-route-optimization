"""Step 1: Haversine screening and authoritative OSRM matrices."""

from dataclasses import dataclass
import json
import math
from typing import Callable, Sequence
from urllib.parse import urlencode
from urllib.request import urlopen

from services.config import OSRM_TIMEOUT_SECONDS, OSRM_URL

Point = tuple[float, float]  # (latitude, longitude)
Matrix = list[list[float]]


@dataclass(frozen=True)
class DistanceMatrixResult:
    points: tuple[Point, ...]
    haversine_km: Matrix
    road_distance_km: Matrix
    road_duration_min: Matrix


def haversine(p1: Point, p2: Point) -> float:
    """Great-circle distance in kilometres."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*p1, *p2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(min(1.0, max(0.0, value))))


def build_haversine_matrix(points: Sequence[Point]) -> Matrix:
    return [[0.0 if i == j else haversine(a, b) for j, b in enumerate(points)]
            for i, a in enumerate(points)]


def cluster_points(points: Sequence[Point], max_radius_km: float) -> list[list[int]]:
    """Connected-component clustering using the fast Haversine matrix."""
    if max_radius_km <= 0:
        raise ValueError("max_radius_km must be positive")
    matrix, unseen, clusters = build_haversine_matrix(points), set(range(len(points))), []
    while unseen:
        stack, component = [unseen.pop()], []
        while stack:
            i = stack.pop(); component.append(i)
            neighbours = {j for j in unseen if matrix[i][j] <= max_radius_km}
            unseen -= neighbours; stack.extend(neighbours)
        clusters.append(sorted(component))
    return clusters


def fetch_osrm_matrices(points: Sequence[Point]) -> tuple[Matrix, Matrix]:
    """Return OSRM road distance (km) and duration (minutes) matrices."""
    if not points:
        return [], []
    coordinates = ";".join(f"{lon},{lat}" for lat, lon in points)
    query = urlencode({"annotations": "distance,duration"})
    url = f"{OSRM_URL.rstrip('/')}/table/v1/driving/{coordinates}?{query}"
    with urlopen(url, timeout=OSRM_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM table error: {payload.get('message', 'unknown error')}")
    distances, durations = payload.get("distances"), payload.get("durations")
    size = len(points)
    if not distances or not durations or len(distances) != size or len(durations) != size:
        raise RuntimeError("OSRM returned incomplete matrices")
    if any(value is None for row in distances + durations for value in row):
        raise RuntimeError("OSRM returned an unreachable point pair")
    return ([[float(v) / 1000.0 for v in row] for row in distances],
            [[float(v) / 60.0 for v in row] for row in durations])


def build_distance_matrix(
    points: Sequence[Point],
    osrm_fetcher: Callable[[Sequence[Point]], tuple[Matrix, Matrix]] = fetch_osrm_matrices,
) -> DistanceMatrixResult:
    """Build fast screening and authoritative road-network matrices."""
    frozen = tuple(points)
    road_distance, road_duration = osrm_fetcher(frozen)
    return DistanceMatrixResult(frozen, build_haversine_matrix(frozen), road_distance, road_duration)
