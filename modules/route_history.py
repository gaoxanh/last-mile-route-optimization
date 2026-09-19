import streamlit as st
import pandas as pd

from database.connection import get_connection

def load_routes():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                route_id,
                batch_id,
                vehicle_id,
                route_type,
                distance_km,
                co2_kg,
                urgent_order_id,
                scenario,
                created_at
            FROM routes
            ORDER BY route_id DESC
            """,
            conn,
        )


def load_stops(route_id):
    with get_connection() as conn:
        return pd.read_sql_query(
            """
        
            SELECT
                rs.sequence,
                rs.order_id,
                rs.distance_from_previous,
                o.customer_id,
                c.latitude,
                c.longitude,
                o.status
            FROM route_stops rs
            LEFT JOIN orders o
                ON o.order_id = rs.order_id
            LEFT JOIN customers c
                ON o.customer_id = c.customer_id
            WHERE rs.route_id = ?
            ORDER BY rs.sequence
            """,
            conn,
            params=(str(route_id),),
        )


routes = load_routes()

st.markdown(
    '<div class="page-heading"><h1>Route history</h1>'
    '<p>Inspect recorded routes, delivery sequence and route-level performance</p></div>',
    unsafe_allow_html=True,
)

if routes.empty:
    st.info(
        "Chưa có route nào được lưu. "
        "Vào Optimization và chạy một batch trước."
    )
    st.stop()


# -------------------------
# ROUTE FILTER
# -------------------------

st.markdown('<div class="panel-title">🗂️ &nbsp;Optimization runs</div>'
            '<div class="panel-sub">Review saved FCFS and optimized routes, including the urgent order and disruption scenario</div>',
            unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    route_types = ["All"] + sorted(
        routes["route_type"].dropna().astype(str).unique().tolist()
    )

    selected_type = st.selectbox(
        "Route Type",
        route_types,
    )

with c2:
    batch_options = ["All"] + sorted(
        routes["batch_id"].dropna().unique().tolist()
    )

    selected_batch = st.selectbox(
        "Delivery Batch",
        batch_options,
    )


filtered = routes.copy()

if selected_type != "All":
    filtered = filtered[
        filtered["route_type"].astype(str) == selected_type
    ]

if selected_batch != "All":
    filtered = filtered[
        filtered["batch_id"] == selected_batch
    ]

if filtered.empty:
    st.warning("Không có route phù hợp bộ lọc.")
    st.stop()


route_labels = {
    f"Route {int(row.route_id)} · {row.route_type} · "
    f"Batch {int(row.batch_id)} · Urgent {row.urgent_order_id or '—'} · {row.scenario or 'Normal'}": int(row.route_id)
    for row in filtered.itertuples()
}

selected_label = st.selectbox(
    "Select Route",
    list(route_labels.keys()),
)

selected_route_id = route_labels[selected_label]

route = filtered[
    filtered["route_id"] == selected_route_id
].iloc[0]

st.divider()


# -------------------------
# ROUTE KPI
# -------------------------

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Route",
    f"#{int(route['route_id'])}",
)


k2.metric(
    "Distance",
    f"{float(route['distance_km']):.2f} km",
)

k3.metric(
    "CO₂",
    f"{float(route['co2_kg']):.2f} kg",
)
stops = load_stops(selected_route_id)


k4.metric(
    "Stops",
    f"{len(stops):,}",
)

st.caption(
    f"**{route['route_type']}** · Batch {int(route['batch_id'])} · "
    f"Vehicle {int(route['vehicle_id'])} · Urgent {route['urgent_order_id'] or '—'} · "
    f"Scenario: {route['scenario'] or 'Normal'}"
)


# -------------------------
# STOP TABLE
# -------------------------

st.divider()
st.markdown('<div class="panel-title">🧭 &nbsp;Delivery sequence</div>'
            '<div class="panel-sub">Stop order and road distance from the previous delivery point</div>',
            unsafe_allow_html=True)

if stops.empty:
    st.warning("Route này chưa có route stops.")
else:
    display_stops = stops.copy()

    display_stops["distance_from_previous"] = (
        display_stops["distance_from_previous"]
        .astype(float)
        .round(2)
    )

    display_stops = display_stops.rename(
        columns={
            "sequence": "Sequence",
            "order_id": "Order ID",
            "customer_id": "Customer",
            "distance_from_previous": "Distance (km)",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "status": "Status",
        }
    )

    st.dataframe(
        display_stops,
        use_container_width=True,
        hide_index=True,
        height=430,
        column_config={
            "Sequence": st.column_config.NumberColumn("Stop", format="%d"),
            "Order ID": st.column_config.TextColumn("Order"),
            "Customer": st.column_config.TextColumn("Customer"),
            "Distance (km)": st.column_config.NumberColumn("Distance (km)", format="%.2f"),
            "Latitude": st.column_config.NumberColumn("Lat", format="%.5f"),
            "Longitude": st.column_config.NumberColumn("Lon", format="%.5f"),
            "Status": st.column_config.TextColumn("Status"),
        },
    )


# -------------------------
# ROUTE MAP
# -------------------------

if {"latitude", "longitude"}.issubset(stops.columns):
    map_df = stops[
        ["latitude", "longitude"]
    ].copy()

    map_df["latitude"] = pd.to_numeric(
        map_df["latitude"],
        errors="coerce",
    )

    map_df["longitude"] = pd.to_numeric(
        map_df["longitude"],
        errors="coerce",
    )

    map_df = map_df.dropna()

    if not map_df.empty:
        st.divider()
        st.markdown('<div class="panel-title">🗺️ &nbsp;Route map</div>'
                    '<div class="panel-sub">Customer stop sequence for the selected route</div>',
                    unsafe_allow_html=True)
        st.map(
            map_df,
            latitude="latitude",
            longitude="longitude",
            size=35,
        )


# -------------------------
# ROUTE DETAILS
# -------------------------

st.divider()
st.markdown('<div class="section-label">Route details</div>', unsafe_allow_html=True)

details = pd.DataFrame({
    "Field": [
        "Route ID",
        "Batch ID",
        "Vehicle ID",
        "Route Type",
        "Total Distance",
        "Total CO₂",
        "Number of Stops",
        "Created At",
    ],
    "Value": [
        route["route_id"],
        route["batch_id"],
        route["vehicle_id"],
        route["route_type"],
        f"{float(route['distance_km']):.2f} km",
        f"{float(route['co2_kg']):.2f} kg",
        len(stops),
        route["created_at"],
    ],
})

st.dataframe(
    details,
    use_container_width=True,
    hide_index=True,
)
