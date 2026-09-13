from services.fcfs import build_fcfs_route


def test_fcfs_orders_by_created_at():
    import pandas as pd

    df = pd.DataFrame([
        {
            "order_id": "O002",
            "customer_id": "KH002",
            "latitude": 10.01,
            "longitude": 106.01,
            "created_at": "2026-08-21 08:05:00",
            "hub_latitude": 10.00,
            "hub_longitude": 106.00,
        },
        {
            "order_id": "O001",
            "customer_id": "KH001",
            "latitude": 10.02,
            "longitude": 106.02,
            "created_at": "2026-08-21 08:01:00",
            "hub_latitude": 10.00,
            "hub_longitude": 106.00,
        },
    ])

    result = build_fcfs_route(df)

    assert result["orders"].iloc[0]["order_id"] == "O001"
    assert result["orders"].iloc[1]["order_id"] == "O002"
    assert result["total_distance_km"] > 0
