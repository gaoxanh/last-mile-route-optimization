from services.two_opt import optimize_2opt


def test_two_opt_does_not_worsen_route():
    hub = (0.0, 0.0)
    customers = [
        (0.0, 0.01),
        (0.01, 0.01),
        (0.01, 0.0),
        (0.02, 0.0),
    ]

    result = optimize_2opt(hub, customers)

    assert result["optimized_distance_km"] <= result["baseline_distance_km"]
    assert len(result["customers"]) == len(customers)


def test_two_opt_keeps_all_customers():
    hub = (10.0, 106.0)
    customers = [
        (10.01, 106.01),
        (10.02, 106.02),
        (10.03, 106.03),
    ]

    result = optimize_2opt(hub, customers)

    assert set(result["customers"]) == set(customers)
