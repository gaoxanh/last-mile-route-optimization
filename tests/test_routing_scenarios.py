import pytest

from services.orchestrator import LastMileRoutingService
from services.routing.bottleneck import Bottleneck, apply_penalties, reroute_remaining
from services.routing.two_opt import route_cost, two_opt


def test_two_opt_improves_matrix_route():
    matrix = [
        [0, 1, 4, 2, 3],
        [1, 0, 2, 5, 4],
        [4, 2, 0, 1, 3],
        [2, 5, 1, 0, 2],
        [3, 4, 3, 2, 0],
    ]
    initial = [0, 1, 3, 2, 4, 0]
    optimized = two_opt(initial, matrix)

    assert route_cost(optimized, matrix) <= route_cost(initial, matrix)
    assert optimized[0] == 0
    assert optimized[-1] == 0
    assert set(optimized) == set(initial)


def test_two_opt_ahead_keeps_urgent_stop_fixed():
    matrix = [
        [0, 4, 2, 7],
        [4, 0, 3, 6],
        [2, 3, 0, 4],
        [7, 6, 4, 0],
    ]
    seed = [1, 2, 3, 0]
    optimized = two_opt(seed, matrix, fix_start=True, fix_end=True)

    assert optimized[0] == 1
    assert optimized[-1] == 0
    assert set(optimized) == set(seed)


def test_penalty_applies_only_to_targeted_directed_edge():
    distance = [
        [0, 10, 20],
        [10, 0, 30],
        [20, 30, 0],
    ]
    duration = [
        [0, 1, 2],
        [1, 0, 3],
        [2, 3, 0],
    ]
    disruptions = [
        Bottleneck(
            from_index=1,
            to_index=2,
            distance_multiplier=1000,
            duration_multiplier=1000,
        )
    ]

    penalized_distance, penalized_duration = apply_penalties(
        distance, duration, disruptions
    )

    assert penalized_distance[1][2] == 30000
    assert penalized_duration[1][2] == 3000
    assert penalized_distance[2][1] == 30
    assert penalized_duration[2][1] == 3
    assert penalized_distance[0][1] == 10


def test_reroute_remaining_preserves_completed_prefix():
    matrix = [
        [0, 2, 5, 4],
        [2, 0, 2, 5],
        [5, 2, 0, 1],
        [4, 5, 1, 0],
    ]
    current = [0, 1, 3, 2, 0]

    rerouted = reroute_remaining(
        current,
        completed_leg_count=2,
        penalized_distance_matrix=matrix,
    )

    assert rerouted[:2] == current[:2]
    assert set(rerouted[2:]) == set(current[2:])


def test_service_normal_run_uses_fcfs_and_optimized_routes(monkeypatch):
    points = [
        (10.0, 106.0),
        (10.01, 106.01),
        (10.02, 106.00),
    ]

    def fake_matrix_builder(_points):
        from services.routing.distance_matrix import DistanceMatrixResult

        road = [
            [0.0, 2.0, 5.0],
            [2.0, 0.0, 2.0],
            [5.0, 2.0, 0.0],
        ]
        duration = [
            [0.0, 2.0, 5.0],
            [2.0, 0.0, 2.0],
            [5.0, 2.0, 0.0],
        ]
        return DistanceMatrixResult(
            tuple(points),
            [[0.0] * 3 for _ in range(3)],
            road,
            duration,
        )

    def fake_legs(route_points):
        distance = 0.0
        for a, b in zip(route_points, route_points[1:]):
            distance += abs(a[0] - b[0]) + abs(a[1] - b[1]) * 100
        return {
            "distance_km": distance,
            "duration_min": distance,
            "geometry": [[p[1], p[0]] for p in route_points],
            "legs": [],
            "points": list(route_points),
        }

    monkeypatch.setattr(
        "services.orchestrator.road_routing.get_route_legs",
        fake_legs,
    )

    stops = [
        {"latitude": points[0][0], "longitude": points[0][1]},
        {"latitude": points[1][0], "longitude": points[1][1]},
        {"latitude": points[2][0], "longitude": points[2][1]},
    ]

    result = LastMileRoutingService(
        stops,
        matrix_builder=fake_matrix_builder,
    ).run(urgent_index=1, scenario="Normal")

    assert result["fcfs_route_indices"][0] == 0
    assert result["fcfs_route_indices"][-1] == 0
    assert result["route_indices"][0] == 0
    assert result["route_indices"][-1] == 0
    assert result["duration_min"] >= 0
    assert result["fcfs_duration_min"] >= 0
