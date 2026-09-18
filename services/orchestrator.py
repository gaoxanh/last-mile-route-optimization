"""Core last-mile routing workflow."""

from typing import Any, Mapping, Sequence

from .config import (
    COMPLETED_LEGS_BEFORE_INCIDENT,
    DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
    TRAFFIC_CLEARANCE_M,
    WEATHER_CLEARANCE_M,
    WEATHER_POSITION_RATIO,
)
from .emission import calculate_co2, calculate_reduction_percent
from .routing import road_routing
from .routing.bottleneck import Bottleneck, apply_penalties, reroute_remaining
from .routing.distance_matrix import DistanceMatrixResult, Point, build_distance_matrix
from .routing.leg_distance import build_leg_distances
from .routing.two_opt import route_cost, two_opt


class LastMileRoutingService:
    """Single source of truth for FCFS, 2-Opt and disruption rerouting."""

    def __init__(
        self,
        stops: Sequence[Mapping[str, object]],
        matrix_builder=build_distance_matrix,
    ):
        if len(stops) < 2:
            raise ValueError("a depot and at least one delivery stop are required")
        self.stops = list(stops)
        self.points: list[Point] = [
            (float(s["latitude"]), float(s["longitude"])) for s in stops
        ]
        self.matrix_builder = matrix_builder
        self.matrices: DistanceMatrixResult | None = None
        self.fcfs_route: list[int] | None = None
        self.route: list[int] | None = None
        self.fcfs_road: dict[str, Any] | None = None
        self.baseline_road: dict[str, Any] | None = None
        self.baseline_route: list[int] | None = None
        self.optimized_road: dict[str, Any] | None = None
        self.active_distance_matrix = None
        self.active_duration_matrix = None
        self.hazards: list[dict[str, Any]] = []
        self.display_hazards: list[dict[str, Any]] = []

    def initialize(self):
        self.matrices = self.matrix_builder(self.points)
        self.active_distance_matrix = [r[:] for r in self.matrices.road_distance_km]
        self.active_duration_matrix = [r[:] for r in self.matrices.road_duration_min]
        self.fcfs_route = list(range(len(self.stops))) + [0]
        return {
            "haversine_km": self.matrices.haversine_km,
            "road_distance_km": self.matrices.road_distance_km,
            "road_duration_min": self.matrices.road_duration_min,
        }

    def optimize(self, urgent_index: int | None = None):
        self._require_initialized()
        if urgent_index is None:
            seed = list(range(len(self.points))) + [0]
            self.route = two_opt(seed, self.active_distance_matrix)
        else:
            if not 1 <= urgent_index < len(self.points):
                raise ValueError("urgent_index must reference a delivery stop")
            remaining = [i for i in range(1, len(self.points)) if i != urgent_index]
            seed = [urgent_index] + remaining + [0]
            suffix = two_opt(seed, self.active_distance_matrix, fix_start=True, fix_end=True)
            self.route = [0] + suffix

        self.baseline_route = self.route[:]
        self.baseline_road = road_routing.get_route_legs(
            [self.points[i] for i in self.baseline_route]
        )
        return self.route[:]

    def simulate_disruption(
        self,
        scenario: str,
        completed_leg_count: int = COMPLETED_LEGS_BEFORE_INCIDENT,
    ):
        self._require_route()
        if scenario not in {"Normal", "Traffic", "Weather", "Both"}:
            raise ValueError(f"unsupported scenario: {scenario}")

        self.hazards = []
        self.display_hazards = []
        if scenario == "Normal":
            self.optimized_road = self.baseline_road
            return self.route[:]

        if not 0 <= completed_leg_count < len(self.route) - 1:
            raise ValueError("completed_leg_count must leave an untravelled suffix")

        baseline_legs = self.baseline_road["legs"]
        positions = []

        if scenario in {"Traffic", "Both"}:
            # With completed_leg_count=1 and urgent O001 this is O001 -> O002.
            positions.append(("traffic", completed_leg_count, TRAFFIC_CLEARANCE_M))

        if scenario in {"Weather", "Both"}:
            pos = min(
                len(baseline_legs) - 1,
                max(
                    completed_leg_count,
                    int(round((len(baseline_legs) - 1) * WEATHER_POSITION_RATIO)),
                ),
            )
            if scenario == "Both" and positions and pos == positions[0][1]:
                pos = min(pos + 1, len(baseline_legs) - 1)
            positions.append(("weather", pos, WEATHER_CLEARANCE_M))

        disruptions = []
        for hazard_type, position, clearance in positions:
            leg = baseline_legs[position]
            point = road_routing.canonical_incident_point(leg["geometry"])
            from_index = self.route[position]
            to_index = self.route[position + 1]
            self.hazards.append({
                "type": hazard_type,
                "leg_index": position,
                "point": point,
                "from_index": from_index,
                "to_index": to_index,
                "clearance_m": clearance,
                "rerouted": False,
            })
            disruptions.append(Bottleneck(
                from_index=from_index,
                to_index=to_index,
                distance_multiplier=1000.0,
                duration_multiplier=1000.0,
                bidirectional=False,
                reason=hazard_type,
            ))

        self.display_hazards = [dict(h) for h in self.hazards]
        self.active_distance_matrix, self.active_duration_matrix = apply_penalties(
            self.matrices.road_distance_km,
            self.matrices.road_duration_min,
            disruptions,
        )
        self.route = reroute_remaining(
            self.route,
            completed_leg_count,
            self.active_distance_matrix,
        )

        current_road = road_routing.get_route_legs(
            [self.points[i] for i in self.route]
        )

        reroute_hazards = []
        for hazard in self.hazards:
            for leg in current_road["legs"]:
                if road_routing._minimum_clearance_m(
                    leg.get("geometry") or [], hazard["point"]
                ) < hazard["clearance_m"]:
                    reroute_hazards.append({**hazard, "leg_index": leg["leg_index"]})
                    break

        if reroute_hazards:
            final_road = road_routing.reroute_route_with_hazards(
                current_road, reroute_hazards
            )
            if not final_road.get("rerouted"):
                failed = [
                    h.get("error", "No valid detour found")
                    for h in final_road.get("hazards", [])
                    if not h.get("rerouted")
                ]
                raise road_routing.RoutingError(
                    "OSRM could not find a valid detour: " + "; ".join(failed)
                )
            self.hazards = final_road.get("hazards", reroute_hazards)
            self.optimized_road = final_road
        else:
            self.optimized_road = current_road
        return self.route[:]

    def result(self):
        self._require_route()
        final_road = self.optimized_road or self.baseline_road
        if self.fcfs_road is None:
            self.fcfs_road = road_routing.get_route_legs(
                [self.points[i] for i in self.fcfs_route]
            )
        fd = float(self.fcfs_road["distance_km"])
        od = float(final_road["distance_km"])
        ft = float(self.fcfs_road["duration_min"])
        ot = float(final_road["duration_min"])
        fco2 = calculate_co2(fd, DEFAULT_MOTORCYCLE_EMISSION_FACTOR)
        oco2 = calculate_co2(od, DEFAULT_MOTORCYCLE_EMISSION_FACTOR)
        return {
            "route_indices": self.route[:],
            "baseline_route_indices": (self.baseline_route or self.route)[:],
            "fcfs_route_indices": self.fcfs_route[:],
            "baseline_distance_km": round(float(self.baseline_road["distance_km"]), 4),
            "baseline_duration_min": round(float(self.baseline_road["duration_min"]), 2),
            "distance_km": round(od, 4),
            "duration_min": round(ot, 2),
            "fcfs_distance_km": round(fd, 4),
            "fcfs_duration_min": round(ft, 2),
            "co2_kg": round(oco2, 4),
            "fcfs_co2_kg": round(fco2, 4),
            "distance_reduction": round(calculate_reduction_percent(fd, od), 2),
            "co2_reduction": round(calculate_reduction_percent(fco2, oco2), 2),
            "legs": build_leg_distances(self.route, self.stops, self.active_distance_matrix),
            "fcfs_road": self.fcfs_road,
            "baseline_road": self.baseline_road,
            "optimized_road": final_road,
            "hazards": self.hazards,
            "display_hazards": self.display_hazards,
        }

    def run(
        self,
        urgent_index: int | None = None,
        scenario: str = "Normal",
        completed_leg_count: int = COMPLETED_LEGS_BEFORE_INCIDENT,
    ):
        self.initialize()
        self.optimize(urgent_index)
        self.fcfs_road = road_routing.get_route_legs(
            [self.points[i] for i in self.fcfs_route]
        )
        self.simulate_disruption(scenario, completed_leg_count)
        return self.result()

    def _require_initialized(self):
        if self.matrices is None:
            raise RuntimeError("call initialize() before optimization")

    def _require_route(self):
        self._require_initialized()
        if self.route is None:
            raise RuntimeError("call optimize() before this operation")
