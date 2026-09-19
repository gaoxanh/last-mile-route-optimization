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
    '<div class="page-heading"><h1>Delivery route history</h1>'
    '<p>Track recorded delivery routes, stop sequence and route progress</p></div>',
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

st.markdown('<div class="panel-title">🚚 &nbsp;Delivery route records</div>'
            '<div class="panel-sub">Follow the delivery sequence, stop status and route performance for recorded delivery runs</div>',
            unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    route_types = ["All"] + sorted(
        routes["route_type"].dropna().astype(str).unique().tolist()
    )

    default_type = "OPTIMIZED" if "OPTIMIZED" in route_types else route_types[0]
    selected_type = st.selectbox(
        "Route plan",
        route_types,
        index=route_types.index(default_type),
        help="Optimized is the operational delivery plan. FCFS is kept as a baseline reference.",
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
    f"Delivery run · Batch {int(row.batch_id)} · "
    f"{row.created_at[:10]} · {row.route_type}": int(row.route_id)
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
# DELIVERY RUN SUMMARY
# -------------------------

stops = load_stops(selected_route_id)

total_stops = len(stops)
if total_stops:
    status_series = stops["status"].fillna("PENDING").astype(str).str.upper()
    delivered_count = int((status_series == "DELIVERED").sum())
    pending_count = int((status_series == "PENDING").sum())
else:
    delivered_count = pending_count = 0

progress = delivered_count / total_stops if total_stops else 0

st.markdown(
    f'<div class="panel-title">🚚 &nbsp;Delivery run · Batch {int(route["batch_id"])}</div>'
    f'<div class="panel-sub">Vehicle {int(route["vehicle_id"])} · '
    f'{route["created_at"]} · {total_stops} recorded stops</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Stops", f"{total_stops}")
k2.metric("Delivered", f"{delivered_count}")
k3.metric("Pending", f"{pending_count}")
k4.metric("Distance", f"{float(route['distance_km']):.2f} km")

st.progress(
    progress,
    text=f"Delivery progress · {delivered_count}/{total_stops} stops delivered"
    if total_stops else "No recorded stops",
)

st.caption(
    f"Route plan: **{route['route_type']}** · CO₂ {float(route['co2_kg']):.2f} kg · "
    f"Urgent {route['urgent_order_id'] or '—'} · Scenario {route['scenario'] or 'Normal'}"
)

if pending_count:
    pending_rows = stops[
        stops["status"].fillna("PENDING").astype(str).str.upper() == "PENDING"
    ]
    if not pending_rows.empty:
        next_stop = pending_rows.iloc[0]
        st.info(
            f"📍 Next pending stop: **#{int(next_stop['sequence'])} · "
            f"Order {next_stop['order_id']}**"
        )


# -------------------------
# STOP TABLE
# -------------------------

st.divider()
st.markdown('<div class="panel-title">🧭 &nbsp;Delivery sequence</div>'
            '<div class="panel-sub">Recorded stop order, delivery status and distance from the previous stop</div>',
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
st.markdown('<div class="panel-title">ℹ️ &nbsp;Delivery run details</div>'
            '<div class="panel-sub">Operational metadata for the selected recorded route</div>',
            unsafe_allow_html=True)

details = pd.DataFrame({
    "Field": [
        "Route ID",
        "Batch ID",
        "Vehicle ID",
        "Route Type",
        "Total Distance",
        "Total CO₂",
        "Number of Stops",
        "Urgent Order",
        "Scenario",
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
        route["urgent_order_id"] or "—",
        route["scenario"] or "Normal",
        route["created_at"],
    ],
})

st.dataframe(
    details,
    use_container_width=True,
    hide_index=True,
)
