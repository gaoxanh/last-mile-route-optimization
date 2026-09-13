from services.distance import haversine, total_route_distance

def test_same_point():
    assert haversine(10.0, 106.0, 10.0, 106.0) == 0.0

def test_distance_is_positive():
    assert haversine(10.0, 106.0, 10.01, 106.01) > 0

def test_route_distance():
    points = [(10.0, 106.0), (10.01, 106.0), (10.01, 106.01)]
    assert total_route_distance(points) > 0
