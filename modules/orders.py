import streamlit as st
import pandas as pd
import pydeck as pdk

from database.connection import get_connection


def load_orders():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM orders
            ORDER BY order_id
            """,
            conn,
        )


def get_order_columns():
    with get_connection() as conn:
        rows = conn.execute("PRAGMA table_info(orders)").fetchall()

    return [row["name"] for row in rows]


df = load_orders()

if df.empty:
    st.info("Chưa có đơn hàng trong database.")
    st.stop()


# -------------------------
# PAGE HEADER / FILTERS
# -------------------------

st.markdown(
    '<div class="page-heading"><h1>Order management</h1>'
    '<p>Review, filter and prepare delivery orders for optimization</p></div>',
    unsafe_allow_html=True,
)

columns = get_order_columns()

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    search = st.text_input(
        "Search Order / Customer",
        placeholder="Ví dụ: O001 hoặc KH001",
    )

with filter_col2:
    status_options = ["All"]

    if "status" in df.columns:
        status_options += sorted(
            df["status"].dropna().astype(str).unique().tolist()
        )

    selected_status = st.selectbox(
        "Status",
        status_options,
    )

with filter_col3:
    batch_options = ["All"]

    if "batch_id" in df.columns:
        batch_options += sorted(
            df["batch_id"].dropna().unique().tolist()
        )

    selected_batch = st.selectbox(
        "Delivery Batch",
        batch_options,
    )


filtered = df.copy()

if search:
    search_lower = search.lower()

    mask = pd.Series(False, index=filtered.index)

    for col in ["order_id", "customer_id"]:
        if col in filtered.columns:
            mask |= (
                filtered[col]
                .astype(str)
                .str.lower()
                .str.contains(search_lower, na=False)
            )

    filtered = filtered[mask]

if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[
        filtered["status"].astype(str) == str(selected_status)
    ]

if selected_batch != "All" and "batch_id" in filtered.columns:
    filtered = filtered[
        filtered["batch_id"] == selected_batch
    ]


# -------------------------
# KPI
# -------------------------

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Orders",
    f"{len(filtered):,}",
)


if "status" in filtered.columns:
    delivered = int(
        (filtered["status"].astype(str).str.upper() == "DELIVERED").sum()
    )
else:
    delivered = 0

k2.metric(
    "Delivered",
    f"{delivered:,}",
    delta=f"{delivered / len(filtered) * 100:.0f}% of view" if len(filtered) else None,
)

if "status" in filtered.columns:
    pending = int(
        (filtered["status"].astype(str).str.upper() == "PENDING").sum()
    )
else:
    pending = 0

k3.metric(
    "Pending",
    f"{pending:,}",
)
if "weight_kg" in filtered.columns:
    total_weight = pd.to_numeric(filtered["weight_kg"], errors="coerce").sum()
else:
    total_weight = 0
k4.metric(
    "Shipment weight",
    f"{total_weight:.1f} kg",
)


# -------------------------
# TABLE
# -------------------------

st.divider()

st.markdown(
    f'<div class="panel-title">📦 &nbsp;Delivery orders</div>'
    f'<div class="panel-sub">{len(filtered):,} orders match the current filters</div>',
    unsafe_allow_html=True,
)

display_df = filtered.copy()

# Keep the table readable without modifying the database.
preferred_order = [
    "order_id",
    "customer_id",
    "batch_id",
    "status",
    "created_at",
    "latitude",
    "longitude",
    "weight_kg",
]

available_preferred = [
    col for col in preferred_order
    if col in display_df.columns
]

remaining = [
    col for col in display_df.columns
    if col not in available_preferred
]

display_df = display_df[
    available_preferred + remaining
]

column_config = {
    "order_id": st.column_config.TextColumn("Order", width="small"),
    "customer_id": st.column_config.TextColumn("Customer", width="small"),
    "batch_id": st.column_config.NumberColumn("Batch", format="%d"),
    "status": st.column_config.TextColumn("Status", width="small"),
    "created_at": st.column_config.DatetimeColumn("Created", format="DD/MM HH:mm"),
    "latitude": st.column_config.NumberColumn("Latitude", format="%.5f"),
    "longitude": st.column_config.NumberColumn("Longitude", format="%.5f"),
    "weight_kg": st.column_config.NumberColumn("Weight (kg)", format="%.1f"),
}

st.dataframe(
    display_df,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    height=430,
)


# -------------------------
# STATUS WORKFLOW
# -------------------------

st.divider()
st.markdown(
    '<div class="panel-title">🔄 &nbsp;Order status</div>'
    '<div class="panel-sub">Update the operational status of a selected delivery order</div>',
    unsafe_allow_html=True,
)

status_values = ["PENDING", "ASSIGNED", "IN_TRANSIT", "DELIVERED", "FAILED"]

if not filtered.empty:
    selected_order = st.selectbox(
        "Selected order",
        filtered["order_id"].astype(str).tolist(),
        key="orders_status_order",
    )
    current_row = filtered[filtered["order_id"].astype(str) == str(selected_order)].iloc[0]
    current_status = str(current_row["status"]).upper()
    new_status = st.selectbox(
        "New status",
        status_values,
        index=status_values.index(current_status) if current_status in status_values else 0,
        key="orders_status_value",
    )

    if st.button("Update order status", type="primary"):
        try:
            with st.spinner("Updating order status..."):
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE orders SET status = ? WHERE order_id = ?",
                        (new_status, int(current_row["order_id"])),
                    )
                    conn.commit()
            st.success(
                f"Order {selected_order} updated to "
                f"{new_status.replace('_', ' ').title()}."
            )
            st.rerun()
        except Exception as exc:
            st.error("Order status could not be updated. Please retry.")
            with st.expander("Technical details"):
                st.code(str(exc))


# -------------------------
# LOCATION PREVIEW
# -------------------------

if {"latitude", "longitude"}.issubset(filtered.columns):
    st.divider()
    st.markdown('<div class="panel-title">📍 &nbsp;Delivery coverage</div>'
                '<div class="panel-sub">Customer locations in the current filtered order set</div>',
                unsafe_allow_html=True)

    map_df = filtered[
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
        map_rows = []
        for row in filtered.loc[map_df.index].itertuples():
            status = str(row.status or "PENDING").upper()
            if status == "DELIVERED":
                color = [54, 130, 85]
            elif status in {"FAILED", "CANCELLED"}:
                color = [205, 72, 72]
            elif status == "IN_TRANSIT":
                color = [70, 120, 205]
            elif status == "ASSIGNED":
                color = [155, 105, 205]
            else:
                color = [220, 165, 45]
            map_rows.append({
                "lat": float(row.latitude),
                "lon": float(row.longitude),
                "label": str(row.order_id),
                "customer": str(row.customer_id),
                "status": status.replace("_", " ").title(),
                "color": color,
            })

        points = pd.DataFrame(map_rows)
        deck = pdk.Deck(
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=points,
                    get_position="[lon, lat]",
                    get_fill_color="color",
                    get_radius=90,
                    radius_min_pixels=6,
                    radius_max_pixels=12,
                    pickable=True,
                ),
                pdk.Layer(
                    "TextLayer",
                    data=points,
                    get_position="[lon, lat]",
                    get_text="label",
                    get_color=[255, 255, 255],
                    get_size=11,
                    get_alignment_baseline="'center'",
                    get_text_anchor="'middle'",
                ),
            ],
            initial_view_state=pdk.ViewState(
                latitude=float(points["lat"].mean()),
                longitude=float(points["lon"].mean()),
                zoom=11.5,
                pitch=0,
            ),
            tooltip={
                "html": "<b>{label}</b><br/>Customer: {customer}<br/>Status: {status}",
                "style": {"backgroundColor": "#263425", "color": "white"},
            },
        )
        st.pydeck_chart(deck, use_container_width=True)
        st.caption("🟢 Delivered · 🔵 In transit · 🟣 Assigned · 🟡 Pending · 🔴 Failed")
