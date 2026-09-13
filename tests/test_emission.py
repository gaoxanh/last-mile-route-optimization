from services.emission import (
    calculate_co2,
    calculate_reduction_percent,
)


def test_calculate_co2():
    assert calculate_co2(100, 0.06) == 6.0


def test_reduction_percent():
    assert calculate_reduction_percent(100, 75) == 25.0
