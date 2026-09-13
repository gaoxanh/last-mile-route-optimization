"""CO2 calculations kept independent from route construction."""

from .config import DEFAULT_MOTORCYCLE_EMISSION_FACTOR


def calculate_co2(
    distance_km: float,
    emission_factor: float = DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
) -> float:
    if distance_km < 0 or emission_factor < 0:
        raise ValueError("distance and emission factor must be non-negative")
    return distance_km * emission_factor


def calculate_reduction_percent(baseline: float, optimized: float) -> float:
    if baseline < 0 or optimized < 0:
        raise ValueError("values must be non-negative")
    return 0.0 if baseline == 0 else (baseline - optimized) / baseline * 100.0
