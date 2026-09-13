"""Main four-step last-mile routing workflow."""

from typing import Mapping, Sequence

from .emission import calculate_co2
from .routing.bottleneck import Bottleneck, apply_penalties, reroute_remaining
from .routing.distance_matrix import DistanceMatrixResult, Point, build_distance_matrix
from .routing.leg_distance import build_leg_distances
from .routing.two_opt import route_cost, two_opt


class LastMileRoutingService:
    def __init__(self, stops: Sequence[Mapping[str, object]], matrix_builder=build_distance_matrix):
        if len(stops) < 2:
            raise ValueError("a depot and at least one delivery stop are required")
        self.stops = list(stops)
        self.points: list[Point] = [(float(s["latitude"]), float(s["longitude"])) for s in stops]
        self.matrix_builder = matrix_builder
        self.matrices: DistanceMatrixResult | None = None
        self.route: list[int] | None = None
        self.active_distance_matrix: list[list[float]] | None = None
        self.active_duration_matrix: list[list[float]] | None = None

    def initialize(self) -> dict[str, object]:
        """Step 1: build original Haversine and OSRM matrices."""
        self.matrices = self.matrix_builder(self.points)
        self.active_distance_matrix = [row[:] for row in self.matrices.road_distance_km]
        self.active_duration_matrix = [row[:] for row in self.matrices.road_duration_min]
        return {"haversine_km": self.matrices.haversine_km,
                "road_distance_km": self.matrices.road_distance_km,
                "road_duration_min": self.matrices.road_duration_min}

    def optimize(self) -> list[int]:
        """Step 2: optimise depot -> deliveries -> depot using road distance."""
        self._require_initialized()
        seed = list(range(len(self.stops))) + [0]
        self.route = two_opt(seed, self.active_distance_matrix)
        return self.route[:]

    def activate_bottlenecks(
        self, disruptions: Sequence[Bottleneck], completed_leg_count: int,
    ) -> list[int]:
        """Step 3: apply penalties and reroute only the untravelled suffix."""
        self._require_route()
        self.active_distance_matrix, self.active_duration_matrix = apply_penalties(
            self.active_distance_matrix, self.active_duration_matrix, disruptions)
        self.route = reroute_remaining(self.route, completed_leg_count, self.active_distance_matrix)
        return self.route[:]

    def result(self) -> dict[str, object]:
        """Step 4: package final legs and aggregate route metrics."""
        self._require_route()
        distance = route_cost(self.route, self.active_distance_matrix)
        duration = route_cost(self.route, self.active_duration_matrix)
        return {"route_indices": self.route[:],
                "distance_km": round(distance, 4),
                "duration_min": round(duration, 2),
                "co2_kg": round(calculate_co2(distance), 4),
                "legs": build_leg_distances(self.route, self.stops, self.active_distance_matrix)}

    def _require_initialized(self) -> None:
        if self.matrices is None:
            raise RuntimeError("call initialize() before optimization")

    def _require_route(self) -> None:
        self._require_initialized()
        if self.route is None:
            raise RuntimeError("call optimize() before this operation")
