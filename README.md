# GreenRoute — Last-Mile Route Optimization

Live Demo: [GreenRoute on Streamlit](https://gaoxanh-greenroute.streamlit.app)

A Streamlit-based academic prototype for **last-mile delivery route optimization and CO₂ estimation**. The system compares a chronological **First-Come, First-Served (FCFS)** baseline with an **urgent-first 2-Opt** route, uses OSRM road-network data for distance and travel time, simulates traffic and weather disruptions, and stores route results in SQLite.

> **Academic prototype:** the current scope is one delivery batch / one vehicle route with a 30-order demonstration dataset. It is not a full multi-vehicle capacitated VRP solver, and disruption data is simulated rather than live.

---

## 1. Project Overview

GreenRoute focuses on two related routing problems:

1. **Initial route planning** — compare FCFS with an urgent-first 2-Opt heuristic.
2. **Mid-route adaptation** — when a simulated disruption affects the planned road, preserve the completed route prefix and re-optimize the uncompleted suffix, followed by road-level detour validation.

The application separates **stop-order optimization** from **road-level routing**:

- **OSRM Table API** provides pairwise road distance and duration used by the optimization heuristic.
- **OSRM Route API** provides actual road geometry and per-leg route metrics shown on the maps.
- **Bottleneck penalties** discourage affected route edges.
- **Waypoint detour logic** checks whether the resulting road geometry still enters the simulated hazard area.

---

## 2. Completed Features

### Routing and optimization

- FCFS baseline sorted by created_at.
- Closed routes: hub → all delivery stops → hub.
- Selected urgent order is fixed as the first delivery stop in the optimized route.
- 2-Opt local search over OSRM road-distance matrices.
- 2-Opt audit showing initial cost, final cost, improvement, and whether the route changed.
- Final route metrics are recalculated from OSRM road geometry.
- FCFS and optimized routes are evaluated using the same road-network basis.

### Disruption simulation

Four scenarios are supported:

| Scenario | Implemented behaviour |
| --- | --- |
| **Normal** | Urgent-first 2-Opt without an active disruption. |
| **Traffic** | Simulated traffic bottleneck placed on an early route leg. |
| **Weather** | Simulated weather hazard placed on a later route leg. |
| **Both** | Simulates both traffic and weather hazards. |

For a disruption scenario:

1. The incident is anchored to an actual point on the planned OSRM road geometry.
2. The affected edge receives a large penalty.
3. The completed prefix of the route is preserved.
4. The remaining suffix is re-optimized.
5. The resulting OSRM geometry is checked against the hazard clearance area.
6. A road-level detour is attempted when the route still enters the hazard zone.

### Environmental metrics

CO₂ is estimated using a constant distance-based emission factor:

~~~text
CO₂ (kg) = route distance (km) × emission factor (kg CO₂/km)
~~~

Current default motorcycle emission factor:

~~~text
0.06 kg CO₂/km
~~~

The factor is configured in services/config.py.

### Database and application

- SQLite persistence for hubs, customers, vehicles, delivery batches, orders, routes, and route stops.
- FCFS and optimized route results can be persisted from the Optimization page.
- Dashboard reads recorded route results from SQLite.
- Route History reads stored route and stop information.
- Orders page provides order filtering and inspection.
- Shared Streamlit shell with green/eco visual design and custom top navigation.

---

## 3. System Workflow

~~~mermaid
flowchart TD
    A["30-order demo dataset"] --> B["FCFS chronological baseline"]
    A --> C["OSRM road-distance / duration matrices"]
    C --> D["Urgent-first seed"]
    D --> E["2-Opt local search"]
    B --> F["FCFS road route"]
    E --> G["Optimized road route"]
    F --> H{"Scenario"}
    G --> H
    H -- "Normal" --> I["Final route metrics"]
    H -- "Traffic / Weather / Both" --> J["Place simulated hazard on route"]
    J --> K["Penalize affected edge"]
    K --> L["Re-optimize uncompleted suffix"]
    L --> M["Check road geometry / hazard clearance"]
    M --> N["Detour if required"]
    N --> I
    I --> O["CO₂ calculation"]
    I --> P["SQLite persistence"]
    O --> Q["Streamlit Dashboard / Route History"]
    P --> Q
~~~

---

## 4. Optimization Logic

### 4.1 FCFS baseline

Orders are sorted chronologically using created_at.

The baseline route is:

~~~text
Hub → Order 1 → Order 2 → ... → Order N → Hub
~~~

The baseline is evaluated using OSRM road routing so that FCFS and optimized routes use the same road-network basis.

### 4.2 Urgent-first 2-Opt

When an urgent order is selected, the optimization seed places that order immediately after the hub:

~~~text
Hub → Urgent Order → Remaining Orders → Hub
~~~

2-Opt then reverses route segments whenever the resulting matrix cost is strictly lower.

The hub remains fixed at the beginning and end of the final route.

### 4.3 Two-level routing architecture

**Level 1 — stop-order optimization**

~~~text
OSRM Table Matrix
      ↓
Urgent-first seed
      ↓
2-Opt
      ↓
Optimized stop sequence
~~~

**Level 2 — road-level adaptation**

~~~text
Optimized stop sequence
      ↓
OSRM Route geometry
      ↓
Simulated road hazard
      ↓
Penalty + suffix rerouting
      ↓
Hazard clearance check
      ↓
OSRM detour
~~~

This separation allows the prototype to demonstrate both route-sequence optimization and physical road detouring.

---

## 5. Application Pages

| Page | Current role |
| --- | --- |
| **Dashboard** | Reads the latest persisted FCFS/optimized route pair from SQLite and summarizes distance, CO₂, route records, and recent runs. |
| **Optimization** | Selects a delivery batch, urgent order, and scenario; runs the routing workflow; displays KPI comparison, 2-Opt audit, and route maps. |
| **Orders** | Inspects and filters delivery orders stored in the application database. |
| **Route History** | Reviews saved routes, stops, route metrics, and historical optimization results. |

The application entrypoint, app.py, is intentionally limited to the shared application shell: page configuration, global CSS, header, and navigation. Page-specific logic lives under modules/.

---

## 6. Maps and Visualization

The Optimization page uses **PyDeck** for route visualization.

Current maps show:

- OSRM road geometry.
- Numbered delivery stops.
- Hub marker.
- Urgent-order marker.
- Traffic/weather hazard marker.
- Hazard clearance area.
- Original route geometry when comparing a rerouted route.
- Separate visual treatment for FCFS, pre-disruption, and post-reroute routes.

Route geometry comes from OSRM rather than simple straight lines between customer coordinates.

---

## 7. Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Application and routing logic |
| Streamlit | Interactive web application |
| pandas | Data processing |
| PyDeck | Interactive route maps |
| Plotly | Data visualization |
| SQLite | Application persistence |
| OSRM | Road distance, duration, and geometry |
| OpenStreetMap | Underlying road-network data |

---

## 8. Project Structure

~~~text
last-mile-route-optimization/
│
├── app.py                              # Streamlit entrypoint + shared UI shell
│
├── modules/
│   ├── dashboard.py                    # Database-driven dashboard
│   ├── optimization.py                 # Optimization workflow + maps
│   ├── orders.py                       # Order management / inspection
│   └── route_history.py                # Saved route history
│
├── services/
│   ├── config.py                       # Routing and emission configuration
│   ├── emission.py                     # CO₂ calculations
│   ├── fcfs.py                         # FCFS chronological ordering
│   ├── orchestrator.py                 # Central routing workflow
│   │
│   └── routing/
│       ├── distance_matrix.py           # Haversine reference + OSRM matrices
│       ├── two_opt.py                   # 2-Opt heuristic + audit
│       ├── bottleneck.py                # Edge penalties + suffix rerouting
│       ├── road_routing.py              # OSRM route geometry + detours
│       └── leg_distance.py              # Per-leg distance information
│
├── database/
│   ├── schema.sql                       # SQLite relational schema
│   ├── connection.py                    # DB connection + schema migrations
│   └── last_mile_co2.db                 # Demonstration database
│
├── data/
│   └── sample_orders.csv                # 30-order demonstration dataset
│
├── tests/
│   └── test_routing_scenarios.py        # Routing and disruption tests
│
└── requirements.txt
~~~

---

## 9. Data and Database Model

The SQLite schema contains seven core entities:

~~~text
Hubs
  │
  └── Delivery Batches ─── Vehicles
          │
          └── Orders ─── Customers
                │
                └── Route Stops ─── Routes
~~~

The Optimization page currently uses the bundled 30-order CSV as the routing demonstration dataset while the selected database batch provides application context and the persistence target.

The batch selector is prepared for future multi-batch expansion; the current optimization demo remains a single 30-order dataset.

---

## 10. Running Locally

### Prerequisites

- Python 3.12+
- Git
- Internet access for the public OSRM endpoint

### Installation

~~~bash
git clone https://github.com/gaoxanh/last-mile-route-optimization.git
cd last-mile-route-optimization

python -m venv .venv
~~~

Windows PowerShell:

~~~powershell
.venvScriptsActivate.ps1
~~~

macOS/Linux:

~~~bash
source .venv/bin/activate
~~~

Install dependencies:

~~~bash
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

Run the application:

~~~bash
streamlit run app.py
~~~

---

## 11. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| OSRM_URL | https://router.project-osrm.org | OSRM server endpoint |
| OSRM_TIMEOUT_SECONDS | 20 | OSRM request timeout |

Example:

~~~bash
export OSRM_URL="http://localhost:5000"
export OSRM_TIMEOUT_SECONDS="30"
streamlit run app.py
~~~

For reproducible or high-volume experiments, a dedicated OSRM instance is preferable to the public demonstration endpoint.

---

## 12. Testing and Validation

The current routing test covers:

- 2-Opt does not worsen matrix route cost.
- Hub start/end constraints.
- Urgent-stop positioning.
- Directed bottleneck penalties.
- Preservation of the completed route prefix during suffix rerouting.
- Normal service execution with FCFS and optimized routes.

Run the current routing test with:

~~~bash
pip install pytest
pytest -q tests/test_routing_scenarios.py
~~~

> The repository may still contain legacy test files from earlier project versions. The current routing test should be treated as the authoritative test file until the test directory is fully cleaned up.

---

## 13. Current Scope and Limitations

### Implemented

- One delivery batch / one route.
- 30 demonstration orders.
- One hub.
- Urgent-first routing.
- FCFS baseline.
- 2-Opt local search.
- OSRM road-network costs.
- Traffic/weather disruption simulation.
- Prefix-preserving suffix rerouting.
- Road-level hazard clearance checking.
- CO₂ estimation.
- SQLite persistence.
- Streamlit visualization.

### Not yet implemented

- Full capacitated multi-vehicle VRP.
- Multiple simultaneous vehicles in the optimizer.
- Time windows and driver shifts.
- Real-time traffic feeds.
- Real-time weather feeds.
- Live road-closure APIs.
- Dynamic vehicle-specific emission models.
- Speed, load, idling, road-grade, and driving-style emission factors.
- Production authentication and role-based access control.

---

## 14. Academic Interpretation

The prototype should be interpreted as a **decision-support and algorithm demonstration system**, not as a production dispatch platform.

The main experimental comparison is:

~~~text
FCFS baseline
     vs.
Urgent-first 2-Opt
     ↓
Road distance / duration
     ↓
CO₂ estimation
     ↓
Disruption response
~~~

For a fair experiment, FCFS and optimized routes should use:

- the same order dataset,
- the same hub,
- the same OSRM endpoint,
- the same return-to-hub convention,
- the same emission factor,
- and the same disruption scenario when applicable.

Under a fixed emission factor, CO₂ reduction is directly proportional to route-distance reduction.

---

## 15. Roadmap

Possible next-stage extensions:

1. Multi-vehicle capacitated VRP using OR-Tools.
2. Time-window constraints.
3. Real-time traffic and weather integration.
4. Vehicle-specific emission models.
5. Reproducible benchmark datasets and experiment logs.
6. Automated CI testing and deployment validation.
7. Authentication and role-based access control.
8. More advanced disruption and recovery strategies.

---

## 16. License

No license file is currently included in the repository. Unless a license is added, the source remains under default copyright.

---

## 17. Author

Developed by [gaoxanh](https://github.com/gaoxanh).
