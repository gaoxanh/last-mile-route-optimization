"""OSRM route geometry helpers used by the optimization map.

Distance-matrix construction remains in ``distance_matrix.py``.  This module
only obtains detailed route geometry and splits a finalized route into legs.
"""

import json
import math
from typing import Any, Sequence
from urllib.parse import urlencode
from urllib.request import urlopen

from services.config import OSRM_TIMEOUT_SECONDS, OSRM_URL
from services.routing.distance_matrix import haversine

Point = tuple[float, float]  # (latitude, longitude)


class RoutingError(RuntimeError):
    """Raised when OSRM cannot construct a road route."""


def get_road_route(points: Sequence[Point]) -> dict[str, Any]:
    """Return distance, duration and GeoJSON coordinates for ordered points."""
    if len(points) < 2:
        return {
            "distance_km": 0.0,
            "duration_min": 0.0,
            "geometry": [[point[1], point[0]] for point in points],
        }

    coordinates = ";".join(f"{lon},{lat}" for lat, lon in points)
    query = urlencode({
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    })
    url = f"{OSRM_URL.rstrip('/')}/route/v1/driving/{coordinates}?{query}"

    try:
        with urlopen(url, timeout=OSRM_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RoutingError(f"Unable to retrieve route from OSRM: {exc}") from exc

    routes = payload.get("routes") or []
    if payload.get("code") != "Ok" or not routes:
        raise RoutingError("OSRM could not find a route")

    route = routes[0]
    return {
        "distance_km": float(route["distance"]) / 1000.0,
        "duration_min": float(route["duration"]) / 60.0,
        "geometry": route["geometry"]["coordinates"],
    }


def get_road_route_alternatives(points: Sequence[Point]) -> list[dict[str, Any]]:
    """Return all alternative routes supplied by OSRM."""
    if len(points) < 2:
        return []
    coordinates = ";".join(f"{lon},{lat}" for lat, lon in points)
    query = urlencode({
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        "alternatives": "true",
    })
    url = f"{OSRM_URL.rstrip('/')}/route/v1/driving/{coordinates}?{query}"
    try:
        with urlopen(url, timeout=OSRM_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RoutingError(f"Unable to retrieve OSRM alternatives: {exc}") from exc
    if payload.get("code") != "Ok":
        raise RoutingError("OSRM could not find alternative routes")
    return [{
        "distance_km": float(route["distance"]) / 1000.0,
        "duration_min": float(route["duration"]) / 60.0,
        "geometry": route["geometry"]["coordinates"],
    } for route in payload.get("routes", [])]


def _bearing(start: Point, end: Point) -> float:
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    delta_lon = lon2 - lon1
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _offset_point(point: Point, bearing_deg: float, distance_m: float) -> Point:
    """Move a coordinate along a great-circle bearing."""
    radius_m = 6_371_000.0
    latitude, longitude = map(math.radians, point)
    bearing = math.radians(bearing_deg)
    angular_distance = distance_m / radius_m
    new_latitude = math.asin(
        math.sin(latitude) * math.cos(angular_distance)
        + math.cos(latitude) * math.sin(angular_distance) * math.cos(bearing)
    )
    new_longitude = longitude + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(latitude),
        math.cos(angular_distance) - math.sin(latitude) * math.sin(new_latitude),
    )
    return math.degrees(new_latitude), math.degrees(new_longitude)


def _minimum_clearance_m(geometry, incident_point):
    """Khoảng cách ngắn nhất từ điểm sự cố đến từng đoạn của polyline."""
    if len(geometry) < 2:
        return 0.0

    lat0, lon0 = incident_point
    scale_x = 111_320.0 * math.cos(math.radians(lat0))
    scale_y = 110_540.0
    minimum = float("inf")

    for start, end in zip(geometry, geometry[1:]):
        ax = (float(start[0]) - lon0) * scale_x
        ay = (float(start[1]) - lat0) * scale_y
        bx = (float(end[0]) - lon0) * scale_x
        by = (float(end[1]) - lat0) * scale_y

        dx, dy = bx - ax, by - ay
        length_squared = dx * dx + dy * dy

        if length_squared == 0:
            distance = math.hypot(ax, ay)
        else:
            t = max(0.0, min(1.0, -(ax * dx + ay * dy) / length_squared))
            distance = math.hypot(ax + t * dx, ay + t * dy)

        minimum = min(minimum, distance)

    return minimum


def find_alternative_route_around_leg(
    leg: dict[str, Any],
    incident_point: Point,
    clearance_m: float = 120.0,
) -> dict[str, Any]:
    """Find a real OSRM detour whose geometry clears the incident radius."""
    start, end = leg["start"], leg["end"]
    original_geometry = leg.get("geometry") or []
    original_distance = float(leg.get("distance_km", 0.0))
    if original_distance <= 0:
        original_distance = get_road_route([start, end])["distance_km"]
    candidates: list[dict[str, Any]] = []

    try:
        alternatives = get_road_route_alternatives([start, end])
    except RoutingError:
        alternatives = []
    for route in alternatives:
        clearance = _minimum_clearance_m(route["geometry"], incident_point)
        # Nới lỏng điều kiện: Cho phép khoảng cách đường vòng dài gấp 8 lần đường cũ để ép tìm ra đường tránh bằng được
        if (route["geometry"] != original_geometry
                and clearance >= clearance_m
                and route["distance_km"] <= original_distance * 8.0 + 5.0):
            candidates.append({**route, "clearance_m": clearance})

    # OSRM public API không thể tự đóng cạnh đường. Ép tạo các waypoint tránh xa hẳn đốm đỏ
    bearing = _bearing(start, end)
    # Thêm nhiều góc bẻ đường (60, 90, 120, 240, 270, 300) và đẩy khoảng cách lệch tâm ra xa hẳn (từ 500m đến 2500m)
    for angle in (60, 90, 120, 240, 270, 300):
        for offset_m in (500.0, 1000.0, 1500.0, 2000.0, 2500.0):
            waypoint = _offset_point(incident_point, bearing + angle, offset_m)
            try:
                route = get_road_route([start, waypoint, end])
            except RoutingError:
                continue
            clearance = _minimum_clearance_m(route["geometry"], incident_point)
            # Chấp nhận các đường vòng xa để đảm bảo an toàn tuyệt đối, vượt qua vùng nghẽn
            if clearance >= clearance_m and route["distance_km"] <= (original_distance * 8.0 + 5.0):
                candidates.append({**route, "clearance_m": clearance})

    # Không hạ chuẩn clearance để "cứu" demo. Nếu không có ứng viên đạt
    # bán kính yêu cầu thì phải báo thất bại, tránh hiển thị một tuyến vẫn đi
    # vào vùng sự cố như thể đã reroute thành công.
    if not candidates:
        raise RoutingError("No OSRM detour satisfies the incident clearance")

    def score(route: dict[str, Any]) -> tuple[float, float]:
        # Phạt tối đa nếu đường vẫn liếm vào vùng nguy hiểm nguy cấp
        if route["clearance_m"] < clearance_m:
            return float('inf'), route["distance_km"]
        added = max(0.0, route["distance_km"] - original_distance)
        # Thưởng lớn cho đường nào tránh càng xa đốm đỏ
        clearance_bonus = (route["clearance_m"] / max(clearance_m, 1.0)) * 5.0
        return added - clearance_bonus, route["distance_km"]



    return min(candidates, key=score)


def reroute_route_with_hazards(
    original_route: dict[str, Any], hazards: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Replace affected leg geometries while preserving stop order."""
    hazards_by_leg: dict[int, list[dict[str, Any]]] = {}
    for hazard in hazards:
        leg_index = hazard.get("leg_index")
        if isinstance(leg_index, int):
            hazards_by_leg.setdefault(leg_index, []).append(hazard)

    route_parts, applied, failed = [], [], []
    for leg in original_route.get("legs", []):
        # Kiểm tra mọi chặng của tuyến mới, không chỉ leg_index cũ.
        leg_hazards = []

        for hazard in hazards:
            clearance_required = float(hazard.get("clearance_m", 120.0))
            actual_clearance = _minimum_clearance_m(
                leg.get("geometry") or [],
                hazard["point"],
            )

            if actual_clearance < clearance_required:
                leg_hazards.append({
                    **hazard,
                    "leg_index": leg["leg_index"],
                })

        if not leg_hazards:
            route_parts.append(leg)
            continue
        strictest = max(leg_hazards, key=lambda item: float(item.get("clearance_m", 120.0)))
        try:
            detour = find_alternative_route_around_leg(
                leg,
                strictest["point"],
                float(strictest.get("clearance_m", 120.0)),
            )
        except RoutingError as exc:
            route_parts.append(leg)
            failed.extend({**item, "rerouted": False, "error": str(exc)} for item in leg_hazards)
            continue
        route_parts.append({**detour, "leg_index": leg["leg_index"],
                            "start": leg["start"], "end": leg["end"]})
        applied.extend({**item, "rerouted": True,
                        "detour_distance_km": detour["distance_km"],
                        "detour_clearance_m": detour["clearance_m"]}
                       for item in leg_hazards)

    return {
        **_merge_route_parts(route_parts),
        "legs": route_parts,
        "points": original_route.get("points", []),
        "hazards": applied + failed,
        "rerouted": bool(applied),
    }


def _merge_route_parts(parts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    geometry: list[list[float]] = []
    distance_km = 0.0
    duration_min = 0.0
    for part in parts:
        part_geometry = part.get("geometry") or []
        geometry.extend(part_geometry if not geometry else part_geometry[1:])
        distance_km += float(part.get("distance_km", 0.0))
        duration_min += float(part.get("duration_min", 0.0))
    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "geometry": geometry,
    }


def get_route_legs(points: Sequence[Point]) -> dict[str, Any]:
    """Fetch individual OSRM legs and merge them for map rendering."""
    frozen_points = list(points)
    legs = []
    for index in range(len(frozen_points) - 1):
        start, end = frozen_points[index], frozen_points[index + 1]
        legs.append({
            **get_road_route([start, end]),
            "leg_index": index,
            "start": start,
            "end": end,
        })
    return {
        **_merge_route_parts(legs),
        "legs": legs,
        "points": frozen_points,
    }


def canonical_incident_point(
    geometry: Sequence[Sequence[float]], fraction: float = 0.5,
) -> Point:
    """Select a point by travelled distance along an OSRM geometry.

    GeoJSON coordinates are ``[longitude, latitude]``.  Selecting by cumulative
    distance avoids the visual offset caused by uneven OSRM vertex density.
    """
    if not geometry:
        raise RoutingError("Cannot create incident point without road geometry")
    if len(geometry) == 1:
        longitude, latitude = geometry[0]
        return float(latitude), float(longitude)

    bounded = min(max(float(fraction), 0.0), 1.0)
    points = [
        (float(latitude), float(longitude))
        for longitude, latitude in geometry
    ]
    segment_lengths = [
        haversine(points[index], points[index + 1])
        for index in range(len(points) - 1)
    ]
    total_length = sum(segment_lengths)
    if total_length == 0:
        return points[0]

    target = total_length * bounded
    travelled = 0.0
    for index, segment_length in enumerate(segment_lengths):
        if travelled + segment_length >= target:
            ratio = 0.0 if segment_length == 0 else (target - travelled) / segment_length
            start_lat, start_lon = points[index]
            end_lat, end_lon = points[index + 1]
            return (
                start_lat + (end_lat - start_lat) * ratio,
                start_lon + (end_lon - start_lon) * ratio,
            )
        travelled += segment_length
    return points[-1]
