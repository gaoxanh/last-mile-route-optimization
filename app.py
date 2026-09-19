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
    box-shadow: 0 10px 25px rgba(57, 76, 56, 0.05) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

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
  .metric-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
  [data-testid="stNavigation"] {margin:0 -1rem 18px; padding:0 .5rem; overflow-x:auto;}
  [data-testid="stNavigation"] a {min-width:135px; padding:12px 10px!important;}
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
