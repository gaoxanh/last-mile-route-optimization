"""Dashboard page using the shared light eco design from app.py."""

import html
import pandas as pd
import streamlit as st

from database.connection import get_connection


def query_df(sql):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


orders_df = query_df("""SELECT COUNT(*) total_orders,
    SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) pending_orders FROM orders""")
routes_df = query_df("""SELECT COUNT(*) total_routes,
    COALESCE(SUM(distance_km),0) total_km, COALESCE(SUM(co2_kg),0) total_co2 FROM routes""")
compare = query_df("""
    SELECT
        f.route_id AS fcfs_route_id,
        o.route_id AS optimized_route_id,
        f.distance_km AS fcfs_km,
        o.distance_km AS optimized_km,
        f.duration_min AS fcfs_duration_min,
        o.duration_min AS optimized_duration_min,
        f.co2_kg AS fcfs_co2,
        o.co2_kg AS optimized_co2,
        o.batch_id,
        o.vehicle_id,
        o.urgent_order_id,
        o.scenario,
        o.created_at
    FROM routes f
    JOIN routes o
      ON o.route_id = (
          SELECT MAX(route_id) FROM routes WHERE route_type = 'OPTIMIZED'
      )
     AND f.route_id = (
          SELECT MAX(route_id)
          FROM routes
          WHERE route_type = 'FCFS'
            AND batch_id = o.batch_id
            AND route_id < o.route_id
      )
""")

total = int(orders_df.iloc[0]["total_orders"] or 0)
pending = int(orders_df.iloc[0]["pending_orders"] or 0)
fcfs_km = float(compare.iloc[0]["fcfs_km"] or 0)
opt_km = float(compare.iloc[0]["optimized_km"] or 0)
fcfs_co2 = float(compare.iloc[0]["fcfs_co2"] or 0)
opt_co2 = float(compare.iloc[0]["optimized_co2"] or 0)
saved_km = max(0.0, fcfs_km - opt_km)
saved_co2 = max(0.0, fcfs_co2 - opt_co2)
km_pct = saved_km / fcfs_km * 100 if fcfs_km else 0
co2_pct = saved_co2 / fcfs_co2 * 100 if fcfs_co2 else 0
urgent_order_id = str(compare.iloc[0]["urgent_order_id"] or "—") if not compare.empty else "—"
scenario = str(compare.iloc[0]["scenario"] or "Normal") if not compare.empty else "—"
batch_id = int(compare.iloc[0]["batch_id"]) if not compare.empty else 0
vehicle_id = int(compare.iloc[0]["vehicle_id"]) if not compare.empty else 0

heading, actions = st.columns([5, 2], vertical_alignment="bottom")
with heading:
    st.markdown('<div class="page-heading"><h1>Operations overview</h1>'
                '<p>Live database snapshot of delivery performance</p></div>',
                unsafe_allow_html=True)
with actions:
    c1, c2 = st.columns([1, 1.15])
    c2.page_link("modules/optimization.py", label="Run optimization", icon="🧭", use_container_width=True)

latest_optimized_km = float(compare.iloc[0]["optimized_km"]) if not compare.empty else 0.0
cards = [("📦", "Total orders", f"{total:,}", ""),
         ("◷", "Pending orders", f"{pending:,}", ""),
         ("🛣️", "Recorded routes", f"{int(routes_df.iloc[0]['total_routes'] or 0):,}", "FCFS + optimized plans"),
         ("📍", "Latest optimized route", f"{latest_optimized_km:.2f} km", "Latest recorded run")]
markup = "".join(
    f'<div class="metric-card"><div class="metric-icon">{icon}</div><div>'
    f'<div class="metric-label">{label}</div><div class="metric-value">{value}'
    f'{("<span class=metric-delta>" + delta + "</span>") if delta else ""}'
    '</div></div></div>' for icon, label, value, delta in cards)
st.markdown(f'<div class="metric-grid">{markup}</div>', unsafe_allow_html=True)


def bars(label, before, after):
    peak = max(before, after, 1)
    return f"""<div style="display:grid;grid-template-columns:110px 1fr 72px;gap:10px;align-items:center;margin:24px 0">
      <b style="font-size:12px">{label}</b><div>
      <div style="height:15px;background:#EDF2EB;border-radius:4px;margin-bottom:8px"><div style="height:100%;width:{before/peak*100:.1f}%;background:#A9C1A5;border-radius:4px"></div></div>
      <div style="height:15px;background:#EDF2EB;border-radius:4px"><div style="height:100%;width:{after/peak*100:.1f}%;background:#394C38;border-radius:4px"></div></div>
      </div><span style="font-size:11px;line-height:23px">{before:.2f}<br><b>{after:.2f}</b></span></div>"""


fcfs_duration = float(compare.iloc[0]["fcfs_duration_min"] or 0) if not compare.empty else 0
opt_duration = float(compare.iloc[0]["optimized_duration_min"] or 0) if not compare.empty else 0

with st.container(border=True):
    st.markdown(
        f'<div class="panel-title">🧭 &nbsp;Latest optimization run</div>'
        f'<div class="panel-sub">Performance is shown for the latest recorded FCFS + optimized pair; the selected urgent order can change the route length.</div>'
        f'<div style="display:flex;gap:28px;flex-wrap:wrap;margin-top:12px;font-size:13px">'
        f'<span><b>Batch:</b> {batch_id}</span>'
        f'<span><b>Vehicle:</b> {vehicle_id}</span>'
        f'<span><b>Urgent:</b> {urgent_order_id}</span>'
        f'<span><b>Scenario:</b> {scenario}</span>'
        f'<span><b>Time:</b> {opt_duration:.0f} min</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f'Latest run: FCFS {fcfs_km:.2f} km → Optimized {opt_km:.2f} km · '
        f'Saved {saved_km:.2f} km ({km_pct:.2f}%) · CO₂ saved {saved_co2:.2f} kg ({co2_pct:.2f}%).'
    )

performance, impact = st.columns([1.85, 1], gap="medium")
with performance:
    with st.container(border=True):
        st.markdown('<div class="panel-title">▥ &nbsp;Route performance</div>'
                    '<div class="panel-sub">Latest recorded FCFS and optimized route pair</div>'
                    '<div style="text-align:right;font-size:10px;color:#71806F">'
                    '<span style="color:#A9C1A5">●</span> FCFS (Current)&nbsp;&nbsp;'
                    '<span style="color:#394C38">●</span> Optimized</div>', unsafe_allow_html=True)
        st.markdown(bars("Total distance", fcfs_km, opt_km), unsafe_allow_html=True)
        st.markdown(bars("CO₂ emissions", fcfs_co2, opt_co2), unsafe_allow_html=True)
with impact:
    with st.container(border=True):
        optimized_share = opt_co2 / fcfs_co2 * 100 if fcfs_co2 else 0
        st.markdown(f"""<div class="panel-title">🍃 &nbsp;Environmental impact</div>
        <div class="panel-sub">CO₂ difference for the latest optimization run</div>
        <div style="display:grid;place-items:center;padding:12px">
        <div style="width:138px;height:138px;border-radius:50%;display:grid;place-items:center;
        background:conic-gradient(#394C38 0 {optimized_share:.1f}%,#B8CEB3 {optimized_share:.1f}% 100%)">
        <div style="width:88px;height:88px;border-radius:50%;background:white;display:grid;place-items:center;text-align:center;color:#263425">
        <span><b style="font-size:18px">{saved_co2:.2f} kg</b><br><small>CO₂ saved</small></span></div></div></div>
        <div class="callout"><strong>🍃 {co2_pct:.2f}% fewer CO₂ emissions</strong>
        <span>A cleaner, greener delivery network.</span></div>""", unsafe_allow_html=True)

recent = query_df("""
    SELECT
        o.route_id AS optimized_route_id,
        f.route_id AS fcfs_route_id,
        o.batch_id,
        o.vehicle_id,
        o.urgent_order_id,
        o.scenario,
        ROUND(f.distance_km, 2) AS fcfs_km,
        ROUND(o.distance_km, 2) AS optimized_km,
        ROUND(o.duration_min, 0) AS duration_min,
        ROUND(f.distance_km - o.distance_km, 2) AS saved_km,
        ROUND(
            CASE WHEN f.distance_km > 0
                 THEN (f.distance_km - o.distance_km) * 100.0 / f.distance_km
                 ELSE 0 END, 1
        ) AS saved_pct,
        ROUND(o.co2_kg, 2) AS co2_kg,
        o.created_at
    FROM routes o
    JOIN routes f
      ON f.route_id = (
          SELECT MAX(f2.route_id)
          FROM routes f2
          WHERE f2.route_type = 'FCFS'
            AND f2.batch_id = o.batch_id
            AND f2.route_id < o.route_id
      )
    WHERE o.route_type = 'OPTIMIZED'
    ORDER BY o.route_id DESC
    LIMIT 6
""")
with st.container(border=True):
    title, link = st.columns([5, 1])
    title.markdown('<div class="panel-title">🚚 &nbsp;Recent routes</div>'
                   '<div class="panel-sub">Latest delivery runs · FCFS vs optimized plan</div>', unsafe_allow_html=True)
    link.page_link("modules/route_history.py", label="View all routes →", use_container_width=True)
    if recent.empty:
        st.info("Chưa có route nào được lưu.")
    else:
        table = recent.rename(columns={
            "optimized_route_id": "Run",
            "batch_id": "Batch",
            "vehicle_id": "Vehicle",
            "urgent_order_id": "Urgent",
            "scenario": "Scenario",
            "fcfs_km": "FCFS (km)",
            "optimized_km": "Optimized (km)",
            "saved_km": "Saved (km)",
            "saved_pct": "Saved (%)",
            "duration_min": "Duration (min)",
            "co2_kg": "CO₂ (kg)",
            "created_at": "Created",
        })
        table["Run"] = table["Run"].map(lambda value: f"#{int(value)}")
        st.dataframe(
            table,
            hide_index=True,
            use_container_width=True,
            height=245,
            column_config={
                "Saved (%)": st.column_config.NumberColumn("Saved (%)", format="%.1f%%"),
                "FCFS (km)": st.column_config.NumberColumn("FCFS (km)", format="%.2f"),
                "Optimized (km)": st.column_config.NumberColumn("Optimized (km)", format="%.2f"),
                "Saved (km)": st.column_config.NumberColumn("Saved (km)", format="%.2f"),
                "Duration (min)": st.column_config.NumberColumn("Duration (min)", format="%.0f"),
                "CO₂ (kg)": st.column_config.NumberColumn("CO₂ (kg)", format="%.2f"),
            },
        )

st.caption(
    f"Database: {int(routes_df.iloc[0]['total_routes'] or 0)} route records · "
    f"Total saved CO₂: {float(routes_df.iloc[0]['total_co2'] or 0):.2f} kg. "
    f"Recorded distance is kept in Route History by individual run."
)
