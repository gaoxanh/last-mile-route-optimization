import io
import json

import services.road_routing as road_routing
import services.route_scenario as route_scenario
from services.two_opt import optimize_2opt


def _fake_route(points):
    legs = []
    geometry = []
    for index in range(len(points) - 1):
        start = points[index]
        end = points[index + 1]
        mid = ((start[0] + end[0]) / 2.0 + 0.001 * index, (start[1] + end[1]) / 2.0)
        leg_geometry = [
            [start[1], start[0]],
            [mid[1], mid[0]],
            [end[1], end[0]],
        ]
        leg = {
            "leg_index": index,
            "start": start,
            "end": end,
            "distance_km": 1.0 + index,
            "duration_min": 2.0,
            "geometry": leg_geometry,
        }
        legs.append(leg)
        geometry.extend(leg_geometry if not geometry else leg_geometry[1:])

    return {
        "distance_km": sum(leg["distance_km"] for leg in legs),
        "duration_min": sum(leg["duration_min"] for leg in legs),
        "geometry": geometry,
        "legs": legs,
        "points": list(points),
    }


def test_scenario_hazards_come_from_actual_route_geometry(monkeypatch):
    monkeypatch.setattr(route_scenario, "get_route_legs", _fake_route)
    hub = (10.0, 106.0)
    customers = [(10.01, 106.01), (10.02, 106.02), (10.03, 106.03)]

    result = route_scenario.build_route_scenario(hub, customers, mode="Traffic")

    assert result["customers"] == customers
    assert result["points"] == [hub] + customers
    assert len(result["hazards"]) == 1

    hazard = result["hazards"][0]
    leg = result["original_route"]["legs"][hazard["leg_index"]]
    assert hazard["type"] == "traffic"
    assert hazard["source_geometry"] == leg["geometry"]
    assert [hazard["point"][1], hazard["point"][0]] in leg["geometry"]
    assert {"type", "leg_index", "point", "source_geometry", "clearance_m"} <= set(hazard)


def test_all_combines_traffic_and_weather_on_different_legs_when_possible(monkeypatch):
    monkeypatch.setattr(route_scenario, "get_route_legs", _fake_route)
    hub = (10.0, 106.0)
    customers = [
        (10.01, 106.01),
        (10.02, 106.02),
        (10.03, 106.03),
        (10.04, 106.04),
    ]

    result = route_scenario.build_route_scenario(hub, customers, mode="All")

    assert [hazard["type"] for hazard in result["hazards"]] == ["traffic", "weather"]
    assert len({hazard["leg_index"] for hazard in result["hazards"]}) == 2


def test_all_handles_single_leg_gracefully(monkeypatch):
    monkeypatch.setattr(route_scenario, "get_route_legs", _fake_route)
    hub = (10.0, 106.0)
    customers = [(10.01, 106.01)]

    result = route_scenario.build_route_scenario(hub, customers, mode="All")

    assert [hazard["type"] for hazard in result["hazards"]] == ["traffic", "weather"]
    assert {hazard["leg_index"] for hazard in result["hazards"]} == {0}


def test_reroute_replaces_only_affected_leg(monkeypatch):
    points = [(10.0, 106.0), (10.01, 106.01), (10.02, 106.02)]
    original_route = _fake_route(points)
    hazard = {
        "type": "traffic",
        "leg_index": 1,
        "point": road_routing.canonical_incident_point(original_route["legs"][1]["geometry"]),
        "source_geometry": original_route["legs"][1]["geometry"],
        "clearance_m": 120.0,
    }
    detour = {
        "distance_km": 4.0,
        "duration_min": 3.0,
        "geometry": [[106.01, 10.01], [106.015, 10.04], [106.02, 10.02]],
        "clearance_m": 200.0,
    }

    monkeypatch.setattr(
        road_routing,
        "find_alternative_route_around_leg",
        lambda leg, point, clearance_m=120.0: detour,
    )

    result = road_routing.reroute_route_with_hazards(original_route, [hazard])

    assert result["points"] == original_route["points"]
    assert result["legs"][0]["geometry"] == original_route["legs"][0]["geometry"]
    assert result["legs"][1]["geometry"] == detour["geometry"]
    assert result["hazards"][0]["point"] == hazard["point"]
    assert result["hazards"][0]["rerouted"] is True


def test_road_distance_matrix_uses_osrm_table(monkeypatch):
    payload = {
        "code": "Ok",
        "distances": [
            [0, 1000],
            [1200, 0],
        ],
    }

    class FakeResponse:
        def __enter__(self):
            return io.StringIO(json.dumps(payload))

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(road_routing, "urlopen", lambda url, timeout=20: FakeResponse())

    matrix = road_routing.get_road_distance_matrix([(10.0, 106.0), (10.1, 106.1)])

    assert matrix == [[0.0, 1.0], [1.2, 0.0]]


def test_two_opt_distance_callback_keeps_urgent_first():
    hub = (0.0, 0.0)
    urgent = (1.0, 0.0)
    customers = [urgent, (0.0, 1.0), (0.0, 2.0)]

    def distance_fn(points):
        return sum(abs(points[i][0] - points[i - 1][0]) + abs(points[i][1] - points[i - 1][1]) for i in range(1, len(points)))

    result = optimize_2opt(hub, customers, fixed_first=urgent, distance_fn=distance_fn)

    assert result["customers"][0] == urgent
    assert set(result["customers"]) == set(customers)
