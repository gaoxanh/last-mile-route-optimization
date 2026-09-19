"""Application entrypoint for the Last-Mile CO₂ Optimization system.

The operational pages live in ``modules/`` and are registered here through
Streamlit navigation. Shared branding and navigation styling remain in this
entrypoint so all pages use the same shell.
"""

from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Last-Mile CO2 Optimization",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -----------------------------------------------------------------------------
# SHARED DESIGN SYSTEM
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root {
  --forest:#263425; --eco:#394C38; --eco-2:#4F6B4C; --sage:#7E9974;
  --mint:#EAF2E8; --canvas:#FFFFFF; --card:#FFFFFF; --line:#D8E2D5;
  --text:#263425; --muted:#71806F; --amber:#A56B16; --amber-bg:#FFF5E5;
}
html, body, [class*="css"] {font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
.stApp {background:var(--canvas); color:var(--text);}
.block-container {max-width:1440px; padding:0 2.2rem 4rem;}
header[data-testid="stHeader"] {height:72px; background:transparent!important; border:0; pointer-events:none;}
footer, [data-testid="stSidebar"] {display:none!important;}
#MainMenu, [data-testid="stToolbar"] {display:flex!important; color:white!important; pointer-events:auto;}
#MainMenu *, [data-testid="stToolbar"] * {color:white!important;}

.app-header {width:100vw; margin:0 calc(50% - 50vw); padding:16px max(2.2rem,calc((100vw - 1440px)/2 + 2.2rem));
  min-height:72px; display:flex;
  align-items:center; color:white; background:linear-gradient(110deg,#203321,#304932 70%,#263E29);
  box-shadow:0 4px 18px rgba(24,43,25,.18);}
.brand {display:flex; align-items:center; gap:12px;}
.brand-mark {width:42px; height:42px; border-radius:12px; display:grid; place-items:center;
  background:rgba(255,255,255,.11); border:1px solid rgba(255,255,255,.14); font-size:23px;}
.brand-title {font-size:20px; font-weight:800; line-height:1.1; letter-spacing:-.3px;}
.brand-sub {margin-top:4px; font-size:11px; color:#C8D8C4;}
.header-actions {margin-left:auto; display:flex; align-items:center; gap:12px;}
.status-pill {padding:7px 12px; border-radius:999px; font-size:11px; font-weight:700;
  border:1px solid rgba(139,218,153,.5); background:rgba(86,161,101,.12); color:#E2F1DF;}
.login-pill {padding:8px 15px; border:1px solid rgba(255,255,255,.48); border-radius:9px;
  font-size:12px; font-weight:700;}

[data-testid="stNavigation"] {margin:0 -2.2rem 22px; padding:0 2.2rem; background:white;
  border-bottom:1px solid var(--line); box-shadow:0 3px 10px rgba(38,52,37,.04);}
[data-testid="stNavigation"] ul {display:flex!important; gap:20px!important; padding:0!important;}
[data-testid="stNavigation"] a {min-width:170px; justify-content:center; padding:15px 20px!important;
  color:#4E5B4C!important; font-size:13px!important; font-weight:700!important;
  border-radius:0!important; border-bottom:3px solid transparent;}
[data-testid="stNavigation"] a:hover {background:#F5F8F3!important; color:var(--eco)!important;}
[data-testid="stNavigation"] a[aria-current="page"] {color:var(--eco)!important;
  background:linear-gradient(180deg,#F6FAF4,#EDF4EA)!important; border-bottom-color:var(--eco);}
.st-key-brand_header {position:sticky;top:0;z-index:990;margin:0!important;}
.st-key-top_navigation {position:sticky;top:72px;z-index:989;width:100vw;
  margin:0 calc(50% - 50vw) 22px!important;padding:0 max(2.2rem,calc((100vw - 1440px)/2 + 2.2rem));
  background:#fff;border-bottom:1px solid var(--line);box-shadow:0 3px 10px rgba(38,52,37,.07);}
div[data-testid="stPageLink"] a {min-height:54px; justify-content:center; gap:9px;
  border:0!important; border-bottom:3px solid transparent!important; border-radius:0!important;
  background:#fff!important; color:#4E5B4C!important; font-size:13px!important; font-weight:750!important;}
div[data-testid="stPageLink"] a * {color:#4E5B4C!important; opacity:1!important;}
div[data-testid="stPageLink"] a:hover {background:#F1F6EF!important; color:var(--eco)!important;
  border-bottom-color:var(--sage)!important;}
div[data-testid="stPageLink"] a:hover * {color:var(--eco)!important;}
div[data-testid="stPageLink"] a[aria-current="page"] {background:linear-gradient(180deg,#F7FAF5,#EBF3E8)!important;
  color:var(--eco)!important; border-bottom-color:var(--eco)!important;}
div[data-testid="stPageLink"] a[aria-current="page"] * {color:var(--eco)!important;}

h1 {font-size:30px!important; line-height:1.15!important; letter-spacing:-.7px!important; margin:0!important;}
h2 {font-size:20px!important; letter-spacing:-.25px!important;}
h3 {font-size:16px!important;}
.page-heading {margin:3px 0 18px;}
.page-heading h1 {font-size:30px; margin:0; color:var(--forest); letter-spacing:-.7px;}
.page-heading p {margin:5px 0 0; color:var(--muted); font-size:13px;}
.section-label {margin:20px 0 10px; font-size:16px; font-weight:800; color:var(--forest);}

.metric-grid {
    display: grid; 
    grid-template-columns: repeat(4, minmax(0,1fr)); 
    gap: 16px; 
    margin: 12px 0 20px;
}

.metric-card {
    min-height: 104px; 
    display: flex; 
    align-items: center; 
    gap: 16px; 
    padding: 18px 20px;
    background: #ffffff !important; 
    border: 1px solid #D2E2CE !important; 
    border-radius: 16px !important; 
    /* Đổ bóng rêu mịn màng diện rộng tạo độ nổi bật */
    box-shadow: 0 10px 25px rgba(57, 76, 56, 0.05) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Hiệu ứng nhấc nhẹ thẻ lên cao và đổi màu viền khi tương tác */
.metric-card:hover {
    transform: translateY(-2px);
    border-color: var(--eco) !important;
    box-shadow: 0 14px 32px rgba(57, 76, 56, 0.1) !important;
}

.metric-icon {flex:0 0 43px; width:43px; height:43px; display:grid; place-items:center;
  border-radius:11px; color:var(--eco); background:var(--mint); font-size:21px;}
.metric-label {font-size:12px; font-weight:700; color:var(--muted); margin-bottom:5px;}
.metric-value {font-size:25px; line-height:1; font-weight:800; letter-spacing:-.5px; color:var(--forest);}
.metric-delta {display:inline-block; margin-left:7px; padding:4px 7px; border-radius:7px;
  color:#28733A; background:#E2F3E3; font-size:10px; font-weight:800; vertical-align:3px;}

.panel-title {font-size:15px; font-weight:800; color:var(--forest); margin:1px 0 2px;}
.panel-sub {font-size:11px; color:var(--muted); margin-bottom:8px;}
.callout {padding:15px 17px; margin:8px 0 15px; border:1px solid #CADAC5; border-radius:12px;
  background:linear-gradient(110deg,#EDF5EA,#F8FBF7); color:var(--forest);}
.callout strong {font-size:14px;} .callout span {display:block; margin-top:4px; color:var(--muted); font-size:11px;}
.route-card {padding:15px; border:1px solid var(--line); border-radius:13px; background:white; margin-bottom:10px;}
.route-card-top {display:flex; justify-content:space-between; gap:10px; font-size:12px; font-weight:800;}
.route-meta {margin-top:7px; font-size:11px; color:var(--muted);}
.badge {display:inline-block; padding:4px 8px; border-radius:999px; background:var(--mint); color:var(--eco); font-size:10px; font-weight:800;}

[data-testid="stVerticalBlockBorderWrapper"] {background:white; border-color:var(--line)!important;
  border-radius:14px!important; box-shadow:0 4px 13px rgba(47,68,46,.045);}
.stButton > button, .stDownloadButton > button {min-height:40px; border-radius:9px!important;
  border:1px solid var(--eco)!important; background:var(--eco)!important; color:white!important;
  font-weight:750!important; box-shadow:0 3px 8px rgba(57,76,56,.12);}
.stButton > button:hover, .stDownloadButton > button:hover {background:#2D402E!important; transform:translateY(-1px);}
[data-testid="stFormSubmitButton"] button {width:100%;}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {
  min-height:40px; border-color:var(--line)!important; border-radius:9px!important; background:white!important;}
[data-testid="stDataFrame"] {border:1px solid var(--line); border-radius:12px; overflow:hidden;}
[data-testid="stTabs"] button {font-weight:700; color:var(--muted);}
[data-testid="stTabs"] button[aria-selected="true"] {color:var(--eco);}
.stAlert {border-radius:11px!important;}
hr {border-color:var(--line)!important;}

@media (max-width:900px) {
  .block-container {padding:0 1rem 3rem;} .app-header {padding:13px 1rem;}
  .brand-title {font-size:17px;} .brand-sub,.status-pill {display:none;}
  [data-testid="stNavigation"] {margin:0 -1rem 18px; padding:0 .5rem; overflow-x:auto;}
  [data-testid="stNavigation"] a {min-width:135px; padding:12px 10px!important;}
  .metric-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media (max-width:560px) {.metric-grid {grid-template-columns:1fr;} .login-pill {display:none;}}
</style>
""",
    unsafe_allow_html=True,
)


def render_header() -> None:
    st.markdown(
        """
        <div class="app-header">
          <div class="brand">
            <div class="brand-mark">🌿</div>
            <div><div class="brand-title">Last-Mile CO₂ Optimization</div>
            <div class="brand-sub">Greener Deliveries · Cleaner Tomorrow</div></div>
          </div>
          <div class="header-actions"><div class="status-pill">● &nbsp;System ready</div>
          <div class="login-pill">Log in</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_heading(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-heading"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def metric_cards(items: list[tuple[str, str, str, str]]) -> None:
    cards = "".join(
        f"""<div class="metric-card"><div class="metric-icon">{icon}</div><div>
        <div class="metric-label">{label}</div><div class="metric-value">{value}
        {f'<span class="metric-delta">{delta}</span>' if delta else ''}</div></div></div>"""
        for icon, label, value, delta in items
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def style_figure(fig, height: int = 310):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=22, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#596656", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(gridcolor="#E7EDE5", zeroline=False)
    fig.update_yaxes(gridcolor="#E7EDE5", zeroline=False)
    return fig


# -----------------------------------------------------------------------------
# PAGE 1 - DASHBOARD
# -----------------------------------------------------------------------------
def dashboard_page() -> None:
    left, right = st.columns([5, 2], vertical_alignment="bottom")
    with left:
        page_heading("Operations overview", "Monitor delivery efficiency and environmental impact")
    with right:
        period, action = st.columns([1, 1.15])
        period.selectbox("Period", ["Last 7 days", "Last 30 days", "This quarter"], index=1, label_visibility="collapsed")
        action.button("Optimize routes", icon="🧭", use_container_width=True)

    metric_cards(
        [
            ("📦", "Total orders", "30", ""),
            ("◷", "Pending orders", "12", ""),
            ("📍", "Distance saved", "189.53 km", "↓ 56.09%"),
            ("🍃", "CO₂ saved", "11.37 kg", "↓ 56.09%"),
        ]
    )

    chart_col, impact_col = st.columns([1.85, 1], gap="medium")
    comparison = pd.DataFrame(
        {"Metric": ["Distance (km)", "Distance (km)", "CO2 (kg)", "CO2 (kg)"],
         "Route": ["FCFS", "Optimized", "FCFS", "Optimized"],
         "Value": [338.96, 149.43, 25.88, 11.37]}
    )
    with chart_col:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Route performance</div><div class="panel-sub">Compare FCFS and optimized route results</div>', unsafe_allow_html=True)
            if px:
                fig = px.bar(comparison, x="Value", y="Metric", color="Route", orientation="h", barmode="group",
                             color_discrete_map={"FCFS": "#A9C1A5", "Optimized": "#394C38"})
                st.plotly_chart(style_figure(fig, 285), use_container_width=True, config={"displayModeBar": False})
            else:
                st.bar_chart(comparison.pivot(index="Metric", columns="Route", values="Value"), color=["#A9C1A5", "#394C38"])
    with impact_col:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Environmental impact</div><div class="panel-sub">Emission reduction after optimization</div>', unsafe_allow_html=True)
            if go:
                fig = go.Figure(go.Pie(values=[11.37, 14.51], labels=["Optimized", "Eliminated"], hole=.66,
                                       marker_colors=["#394C38", "#B8CEB3"], textinfo="percent"))
                fig.add_annotation(text="<b>11.37 kg</b><br><span style='font-size:10px'>CO2 saved</span>", showarrow=False)
                st.plotly_chart(style_figure(fig, 235), use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="callout"><strong>🍃 56.09% fewer CO₂ emissions</strong><span>A cleaner, greener delivery network.</span></div>', unsafe_allow_html=True)

    with st.container(border=True):
        title_col, link_col = st.columns([5, 1])
        title_col.markdown('<div class="panel-title">🚚 &nbsp;Recent routes</div><div class="panel-sub">Latest optimized delivery routes</div>', unsafe_allow_html=True)
        link_col.button("View all routes", type="tertiary", use_container_width=True)
        st.dataframe(routes.head(6).drop(columns="Date"), hide_index=True, use_container_width=True, height=250)


# -----------------------------------------------------------------------------
# PAGE 2 - OPTIMIZATION
# -----------------------------------------------------------------------------
def optimization_page() -> None:
    page_heading("Route optimization", "Configure constraints, generate routes and compare efficiency")
    metric_cards(
        [("📦", "Orders ready", "30", ""), ("🚚", "Available vehicles", "6", ""),
         ("📏", "Estimated distance", "149.43 km", "↓ 56.09%"), ("🍃", "Estimated CO₂", "11.37 kg", "↓ 56.09%")]
    )

    settings, workspace = st.columns([1, 2.05], gap="medium")
    with settings:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Optimization settings</div><div class="panel-sub">Define operational constraints</div>', unsafe_allow_html=True)
            with st.form("optimizer"):
                algorithm = st.selectbox("Algorithm", ["Genetic Algorithm", "Nearest Neighbor", "OR-Tools VRP"])
                vehicle_count = st.number_input("Number of vehicles", 1, 20, 6)
                capacity = st.number_input("Vehicle capacity (kg)", 10, 1000, 120, step=10)
                max_distance = st.slider("Maximum route distance (km)", 20, 200, 80)
                avoid_hazards = st.toggle("Avoid disruptions and hazards", value=True)
                submitted = st.form_submit_button("Generate optimized routes", icon="🧭")
        with st.container(border=True):
            st.markdown('<div class="panel-title">Optimization priorities</div>', unsafe_allow_html=True)
            st.slider("Distance", 0, 100, 55, disabled=True)
            st.slider("CO₂ emissions", 0, 100, 30, disabled=True)
            st.slider("Delivery time", 0, 100, 15, disabled=True)

    with workspace:
        tab_map, tab_compare = st.tabs(["Route map", "Performance comparison"])
        with tab_map:
            with st.container(border=True):
                st.markdown('<div class="panel-title">Optimized delivery network</div><div class="panel-sub">Hub and delivery stops for the current batch</div>', unsafe_allow_html=True)
                map_data = orders[["Latitude", "Longitude"]].rename(columns={"Latitude": "lat", "Longitude": "lon"})
                st.map(map_data, latitude="lat", longitude="lon", size=45, color="#4F6B4C", height=410)
                st.caption("● Hub: District 1  ·  ● 30 delivery stops  ·  6 proposed routes")
        with tab_compare:
            with st.container(border=True):
                compare = pd.DataFrame({"Metric": ["Distance", "CO2", "Duration"], "FCFS": [338.96, 25.88, 9.8], "Optimized": [149.43, 11.37, 6.2]})
                st.dataframe(compare, hide_index=True, use_container_width=True)
                if px:
                    melted = compare.melt("Metric", var_name="Method", value_name="Value")
                    fig = px.bar(melted, x="Metric", y="Value", color="Method", barmode="group",
                                 color_discrete_map={"FCFS": "#A9C1A5", "Optimized": "#394C38"})
                    st.plotly_chart(style_figure(fig, 305), use_container_width=True, config={"displayModeBar": False})

    if submitted:
        st.success(f"Optimization completed with {algorithm}: {vehicle_count} vehicles, {capacity} kg capacity, {max_distance} km limit" + (", hazard avoidance enabled." if avoid_hazards else "."))

    st.markdown('<div class="section-label">Proposed routes</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for index in range(6):
        with cols[index % 3]:
            st.markdown(f'<div class="route-card"><div class="route-card-top"><span>Route {index + 1:02d}</span><span class="badge">Optimized</span></div><div class="route-meta">Van {index % 3 + 1} · 5 stops · {22.4 + index * 1.7:.1f} km · {1.7 + index * .13:.2f} kg CO₂</div></div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# PAGE 3 - ORDERS
# -----------------------------------------------------------------------------
def orders_page() -> None:
    heading, action = st.columns([5, 1.2], vertical_alignment="bottom")
    with heading:
        page_heading("Order management", "Review, filter and prepare delivery orders for optimization")
    with action:
        if st.button("Add new order", icon="＋", use_container_width=True):
            st.session_state.show_order_form = True

    metric_cards(
        [("📦", "All orders", "30", ""), ("◷", "Pending", "12", ""),
         ("🚚", "Assigned", "8", ""), ("✓", "Delivered", "10", "")]
    )

    if st.session_state.get("show_order_form", False):
        with st.expander("Create order", expanded=True):
            with st.form("new_order"):
                c1, c2, c3 = st.columns(3)
                customer = c1.text_input("Customer name")
                district = c2.selectbox("District", sorted(orders["District"].unique()))
                priority = c3.selectbox("Priority", ["Normal", "High", "Urgent"])
                address = st.text_input("Delivery address")
                c4, c5 = st.columns(2)
                weight = c4.number_input("Weight (kg)", 0.1, 500.0, 5.0)
                window = c5.selectbox("Time window", ["08:00 - 10:00", "10:00 - 12:00", "13:00 - 15:00", "15:00 - 17:00"])
                if st.form_submit_button("Save order"):
                    st.success(f"Order for {customer or 'new customer'} saved as a draft.")

    with st.container(border=True):
        search_col, status_col, priority_col, export_col = st.columns([2.3, 1.1, 1.1, 1])
        search = search_col.text_input("Search", placeholder="Search order ID or customer...", label_visibility="collapsed")
        status = status_col.selectbox("Status", ["All statuses", "Pending", "Assigned", "Delivered"], label_visibility="collapsed")
        priority = priority_col.selectbox("Priority", ["All priorities", "Normal", "High", "Urgent"], label_visibility="collapsed")
        filtered = orders.copy()
        if search:
            mask = filtered["Order ID"].str.contains(search, case=False) | filtered["Customer"].str.contains(search, case=False)
            filtered = filtered[mask]
        if status != "All statuses":
            filtered = filtered[filtered["Status"] == status]
        if priority != "All priorities":
            filtered = filtered[filtered["Priority"] == priority]
        export_col.download_button("Export CSV", filtered.to_csv(index=False).encode(), "orders.csv", "text/csv", use_container_width=True)
        display = filtered.drop(columns=["Latitude", "Longitude"])
        st.dataframe(display, hide_index=True, use_container_width=True, height=500,
                     column_config={"Weight (kg)": st.column_config.NumberColumn(format="%.1f kg")})
        st.caption(f"Showing {len(filtered)} of {len(orders)} orders")


# -----------------------------------------------------------------------------
# PAGE 4 - ROUTE HISTORY
# -----------------------------------------------------------------------------
def route_history_page() -> None:
    page_heading("Route history", "Track completed routes and measure optimization performance over time")
    metric_cards(
        [("🛣️", "Recorded routes", "18", ""), ("📏", "Total distance", "486.26 km", ""),
         ("🍃", "Total CO₂", "29.18 kg", ""), ("↘", "Average reduction", "56.09%", "")]
    )

    trends, breakdown = st.columns([1.75, 1], gap="medium")
    with trends:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Distance trend</div><div class="panel-sub">Daily route distance by method</div>', unsafe_allow_html=True)
            trend = routes.groupby(["Date", "Type"], as_index=False)["Distance (km)"].sum()
            if px:
                fig = px.line(trend, x="Date", y="Distance (km)", color="Type", markers=True,
                              color_discrete_map={"FCFS": "#A9C1A5", "Optimized": "#394C38"})
                st.plotly_chart(style_figure(fig, 285), use_container_width=True, config={"displayModeBar": False})
            else:
                st.line_chart(trend.pivot(index="Date", columns="Type", values="Distance (km)"))
    with breakdown:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Route type breakdown</div><div class="panel-sub">Recorded routes by planning method</div>', unsafe_allow_html=True)
            if go:
                counts = routes["Type"].value_counts()
                fig = go.Figure(go.Pie(values=counts.values, labels=counts.index, hole=.62,
                                       marker_colors=["#394C38", "#B8CEB3"], textinfo="label+percent"))
                st.plotly_chart(style_figure(fig, 285), use_container_width=True, config={"displayModeBar": False})

    with st.container(border=True):
        st.markdown('<div class="panel-title">Route records</div><div class="panel-sub">Search and inspect historical route performance</div>', unsafe_allow_html=True)
        search_col, type_col, status_col, export_col = st.columns([2.2, 1, 1, 1])
        query = search_col.text_input("Search route", placeholder="Search route ID...", label_visibility="collapsed")
        route_type = type_col.selectbox("Type", ["All types", "Optimized", "FCFS"], label_visibility="collapsed")
        route_status = status_col.selectbox("Route status", ["All statuses", "Completed", "Active"], label_visibility="collapsed")
        history = routes.copy()
        if query:
            history = history[history["Route ID"].str.contains(query, case=False)]
        if route_type != "All types":
            history = history[history["Type"] == route_type]
        if route_status != "All statuses":
            history = history[history["Status"] == route_status]
        export_col.download_button("Export CSV", history.to_csv(index=False).encode(), "route_history.csv", "text/csv", use_container_width=True)
        st.dataframe(history, hide_index=True, use_container_width=True, height=410,
                     column_config={"Distance (km)": st.column_config.NumberColumn(format="%.2f km"),
                                    "CO2 (kg)": st.column_config.NumberColumn(format="%.2f kg")})


# Register real module pages first, then render a stable custom top navigation.
pages = [
    st.Page("modules/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("modules/optimization.py", title="Optimization", icon="🗺️"),
    st.Page("modules/orders.py", title="Orders", icon="📦"),
    st.Page("modules/route_history.py", title="Route History", icon="🛣️"),
]
navigation = st.navigation(pages, position="hidden")
with st.container(key="brand_header"):
    render_header()
with st.container(key="top_navigation"):
    nav_columns = st.columns(4, gap="small")
    with nav_columns[0]:
        st.page_link("modules/dashboard.py", label="Dashboard", icon="📊", use_container_width=True)
    with nav_columns[1]:
        st.page_link("modules/optimization.py", label="Optimization", icon="🗺️", use_container_width=True)
    with nav_columns[2]:
        st.page_link("modules/orders.py", label="Orders", icon="📦", use_container_width=True)
    with nav_columns[3]:
        st.page_link("modules/route_history.py", label="Route History", icon="🛣️", use_container_width=True)
navigation.run()
