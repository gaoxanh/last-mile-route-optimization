import streamlit as st
import pandas as pd

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

k1, k2, k3 = st.columns(3)

k1.metric(
    "Total Orders",
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


# -------------------------
# TABLE
# -------------------------

st.divider()

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

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# -------------------------
# LOCATION PREVIEW
# -------------------------

if {"latitude", "longitude"}.issubset(filtered.columns):
    st.divider()
    st.markdown('<div class="section-label">Order locations</div>', unsafe_allow_html=True)

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
        st.map(
            map_df,
            latitude="latitude",
            longitude="longitude",
            size=30,
        )
