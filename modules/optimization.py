from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt

try:
    import pydeck as pdk
except ImportError:  # pragma: no cover - optional dependency for map rendering
    pdk = None

from database.connection import get_connection
from services.emission import (
    DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
    calculate_co2,
    calculate_reduction_percent,
)
from services.fcfs import build_fcfs_route
from services.routing import road_routing
from services.routing.bottleneck import Bottleneck, apply_penalties, reroute_remaining
from services.routing.distance_matrix import build_distance_matrix
from services.routing.leg_distance import build_leg_distances
from services.routing.two_opt import route_cost, two_opt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"

# Bảng màu chuẩn RGBA
COLOR_FCFS = [30, 64, 175, 255]       # Blue đậm (FCFS)
COLOR_BEFORE = [109, 40, 217, 255]    # Purple đậm (Trước sự cố)
COLOR_AFTER = [220, 38, 38, 255]      # Red (Đã Reroute né sự cố)
COLOR_URGENT = [234, 179, 8, 255]     # Yellow (Đơn hàng gấp)
COLOR_HUB = [249, 115, 22, 255]       # Orange (Kho tổng)

def get_batches():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT db.batch_id, db.delivery_date, db.status, db.vehicle_id, v.vehicle_type
            FROM delivery_batches db
            JOIN vehicles v ON v.vehicle_id = db.vehicle_id
            ORDER BY db.batch_id
            """
        ).fetchall()

def _calculate_zoom(points):
    if not points:
        return 11
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    span = max(max(lats) - min(lats), max(lons) - min(lons))
    if span < 0.01: return 13
    if span < 0.03: return 12
    if span < 0.07: return 11
    if span < 0.15: return 10
    if span < 0.30: return 9
    return 8

def _build_marker_dataframe(route_orders, urgent_order_id, color_theme):
    """Tạo Marker điểm dừng đồng bộ tọa độ chuẩn hóa."""
    rows = []
    for sequence, row in enumerate(route_orders, start=1):
        order_id = str(row["order_id"])
        is_urgent = order_id == str(urgent_order_id)
        color = COLOR_URGENT if is_urgent else color_theme

        rows.append({
            "sequence": sequence,
            "label": str(sequence),
            "order_id": order_id,
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "urgent": "Có (Khẩn cấp)" if is_urgent else "Không",
            "color": color,
        })
    return pd.DataFrame(rows)

def build_single_map(hub, orders, road_geometry, color_path, color_marker, urgent_id, disruption=None, hazards=None, old_geometry=None):
    """Hàm dựng bản đồ độc lập sửa lỗi hiển thị và thêm nét vẽ đường cũ xám mờ."""
    hub_lat, hub_lon = hub
    points = [(hub_lat, hub_lon)] + [(float(r["latitude"]), float(r["longitude"])) for r in orders]
    
    # SỬA LỖI ĐOẠN NÀY: Bảo toàn hình học mượt mà từ OSRM trả về thay vì ép vẽ đường thẳng thô
    path_data = road_geometry if road_geometry else [[p[1], p[0]] for p in points]

    layers = []

    # CẢI TIẾN 1: Vẽ đoạn đường cũ bị thay thế bằng màu xám mờ (Dành riêng cho Map 2)
    if old_geometry:
        layers.append(pdk.Layer(
            "PathLayer", id=f"old-decayed-route-{color_path[0]}", data=[{"path": old_geometry}],
            get_path="path", get_color=[156, 163, 175, 180], # Màu xám mờ tinh tế (Gray-400)
            width_min_pixels=4, width_max_pixels=6, pickable=False
        ))

    # 1. Tuyến đường chính (Đỏ hoặc Tím)
    layers.append(pdk.Layer(
        "PathLayer", id=f"main-route-{color_path[0]}", data=[{"path": path_data}],
        get_path="path", get_color=color_path, width_min_pixels=5, width_max_pixels=8, pickable=False
    ))
    
    # 2. Markers điểm dừng & Số STT hiển thị to rõ
    marker_df = _build_marker_dataframe(orders, urgent_id, color_marker)
    if not marker_df.empty:
        layers.extend([
            pdk.Layer(
                "ScatterplotLayer", id=f"customer-pins-{color_path[0]}", data=marker_df,
                get_position="[longitude, latitude]", get_fill_color="color",
                get_radius=100, radius_min_pixels=14, radius_max_pixels=24,
                stroked=True, get_line_color=[255, 255, 255, 255], line_width_min_pixels=1.5,
                pickable=True
            ),
            pdk.Layer(
                "TextLayer", id=f"customer-labels-{color_path[0]}", data=marker_df,
                get_position="[longitude, latitude]", get_text="label",
                get_size=16, get_color=[255, 255, 255, 255],
                get_text_anchor="middle", get_alignment_baseline="center",
                font_weight="bold", billboard=True, pickable=False
            )
        ])

    # 3. Hub Kho hàng ★
    hub_df = pd.DataFrame([{"latitude": hub_lat, "longitude": hub_lon, "label": "🏠"}])
    layers.extend([
        pdk.Layer(
            "ScatterplotLayer", id=f"hub-point-{color_path[0]}", data=hub_df,
            get_position="[longitude, latitude]", get_radius=150,
            radius_min_pixels=18, radius_max_pixels=26, get_fill_color=COLOR_HUB, pickable=False
        ),
        pdk.Layer(
            "TextLayer", id=f"hub-label-{color_path[0]}", data=hub_df,
            get_position="[longitude, latitude]", get_text="label",
            get_size=18, get_text_anchor="middle", get_alignment_baseline="center",
            font_weight="bold", billboard=True, pickable=True
        )
    ])

    # 4. Icon sự cố 🚧 và Vòng tròn vùng nghẽn an toàn
    if disruption is None and hazards:
        disruption = hazards[0]

    normalized_hazards = list(hazards or [])
    if disruption:
        first_match = (
            normalized_hazards
            and normalized_hazards[0].get("leg_index") == disruption.get("leg_index")
            and normalized_hazards[0].get("point") == disruption.get("point")
        )
        if not first_match:
            normalized_hazards = [disruption] + normalized_hazards

    if disruption:
        disruption_df = pd.DataFrame([{
            "latitude": disruption["point"][0],
            "longitude": disruption["point"][1],
            "text": "🚧",
            "radius": disruption.get("clearance_m", 120.0)
        }])
        layers.extend([
            pdk.Layer(
                "ScatterplotLayer", id=f"incident-outer-{color_path[0]}", data=disruption_df,
                get_position="[longitude, latitude]", get_radius="radius", # Vẽ chuẩn bán kính nghẽn thực địa
                get_fill_color=[239, 68, 68, 80], # Đỏ mờ trong suốt để nhìn thấy đường đi bên dưới
                get_line_color=[185, 28, 28, 255],
                stroked=True, line_width_min_pixels=2, pickable=True
            ),
            pdk.Layer(
                "TextLayer", id=f"incident-text-{color_path[0]}", data=disruption_df,
                get_position="[longitude, latitude]", get_text="text",
                get_size=24, get_text_anchor="middle", get_alignment_baseline="center",
                font_family="Segoe UI Emoji, Apple Color Emoji, Arial, sans-serif",
                billboard=True, pickable=False
            )
        ])

    extra_hazards = normalized_hazards[1:]
    if extra_hazards:
        extra_hazard_df = pd.DataFrame([
            {
                "latitude": hazard["point"][0],
                "longitude": hazard["point"][1],
                "text": "🚧",
                "radius": hazard.get("clearance_m", 120.0)
            }
            for hazard in extra_hazards
        ])
        layers.extend([
            pdk.Layer(
                "ScatterplotLayer", id=f"extra-incident-outer-{color_path[0]}", data=extra_hazard_df,
                get_position="[longitude, latitude]", get_radius="radius",
                get_fill_color=[239, 68, 68, 80],
                get_line_color=[185, 28, 28, 255],
                stroked=True, line_width_min_pixels=2, pickable=True
            ),
            pdk.Layer(
                "TextLayer", id=f"extra-incident-text-{color_path[0]}", data=extra_hazard_df,
                get_position="[longitude, latitude]", get_text="text",
                get_size=24, get_text_anchor="middle", get_alignment_baseline="center",
                font_weight="bold", billboard=True, pickable=False
            )
        ])

    return pdk.Deck(
        map_provider="carto", map_style="road",
        initial_view_state=pdk.ViewState(
            latitude=sum(p[0] for p in points) / len(points),
            longitude=sum(p[1] for p in points) / len(points),
            zoom=_calculate_zoom(points), pitch=0, bearing=0, controller=True
        ),
        layers=layers,
        tooltip={"html": "<b>Điểm dừng {sequence}</b><br/>Đơn hàng ID: {order_id}<br/>Trạng thái gấp: {urgent}"}
    )

# --- PAGE HEADER / CONFIGURATION ---
st.markdown(
    '<div class="page-heading"><h1>Route optimization</h1>'
    '<p>Configure constraints, generate routes and compare efficiency</p></div>',
    unsafe_allow_html=True,
)

batches = get_batches()
if not batches:
    st.warning("Chưa có dữ liệu delivery batch trong hệ thống database.")
    st.stop()

with st.expander("⚙️ Optimization settings", expanded=True):
    st.markdown('<div class="panel-sub">Select a delivery batch, priority order and road scenario</div>', unsafe_allow_html=True)
    batch_options = {f"Batch {row['batch_id']} ({row['delivery_date']})": row for row in batches}
    selected_label = st.selectbox("📦 Lựa chọn Delivery Batch", list(batch_options.keys()))
    selected_batch = batch_options[selected_label]

    st.info(f"**Phương tiện:** {selected_batch['vehicle_type']}\n\n**Trạng thái xử lý:** {selected_batch['status']}")

    if not CSV_PATH.exists():
        st.error(f"Không tìm thấy tập dữ liệu mẫu: {CSV_PATH}")
        st.stop()

    preview_df = pd.read_csv(CSV_PATH)
    urgent_options = preview_df["order_id"].astype(str).tolist()
    urgent_order_id = st.selectbox("🚨 Chỉ định Đơn hàng Ưu tiên (Urgent)", urgent_options, index=0)
    scenario = st.selectbox("🌧️ Kịch bản điều kiện tuyến đường (Scenario)", ["Normal", "Traffic", "Weather", "Both"])

    run_btn = st.button("🚀 Thực thi tối ưu hóa toàn tuyến", type="primary", use_container_width=True)

if run_btn:
    df = preview_df.copy()
    fcfs = build_fcfs_route(df)
    fcfs_orders = fcfs["orders"].copy()

    urgent_rows = fcfs_orders[fcfs_orders["order_id"].astype(str) == str(urgent_order_id)]
    if urgent_rows.empty:
        st.error(f"Không tìm thấy đơn hàng ưu tiên mang mã số {urgent_order_id}.")
        st.stop()

    # Bước 1: tạo ma trận Haversine và ma trận đường bộ OSRM.
    fcfs_points = [fcfs["hub"]] + [
        (float(r["latitude"]), float(r["longitude"]))
        for r in fcfs_orders.to_dict("records")
    ]
    matrices = build_distance_matrix(fcfs_points)
    road_matrix = matrices.road_distance_km
    duration_matrix = matrices.road_duration_min

    # FCFS là tuyến mở: kho -> các điểm theo created_at.
    fcfs_route = list(range(len(fcfs_points)))
    fcfs_dist = round(route_cost(fcfs_route, road_matrix), 2)

    urgent_position = urgent_rows.index[0]
    urgent_index = fcfs_orders.index.get_loc(urgent_position) + 1
    remaining_indices = [i for i in range(1, len(fcfs_points)) if i != urgent_index]

    # Bước 2: giữ đơn khẩn cấp ở đầu, dùng 2-opt cho phần còn lại và quay về kho.
    optimized_suffix = two_opt(
        [urgent_index] + remaining_indices + [0],
        road_matrix,
        fix_start=True,
        fix_end=True,
    )
    baseline_route = [0] + optimized_suffix
    baseline_distance = round(route_cost(baseline_route, road_matrix), 2)

    def records_from_route(route_indices):
        return [fcfs_orders.iloc[index - 1].to_dict() for index in route_indices[1:-1]]

    baseline_route_orders = records_from_route(baseline_route)
    current_route = baseline_route[:]
    active_distance_matrix = [row[:] for row in road_matrix]
    active_duration_matrix = [row[:] for row in duration_matrix]
    hazards = []

    # Giữ danh sách sự cố gốc riêng cho UI. Không để kết quả reroute
    # loại mất sự cố đã được né khỏi bản đồ khi chọn scenario = All.
    display_hazards = []

    # Geometry tuyến trước sự cố được dùng để chọn và hiển thị điểm nghẽn.
    fcfs_road = road_routing.get_route_legs(fcfs_points)
    baseline_optimized_road = road_routing.get_route_legs([fcfs["hub"]] + [
        (float(r["latitude"]), float(r["longitude"]))
        for r in baseline_route_orders
    ] + [fcfs["hub"]])

    # Bước 3: phạt cạnh bị nghẽn rồi chạy lại 2-opt trên phần chưa giao.
    # =========================================================================
    # BƯỚC 3: CẤU HÌNH CỐ ĐỊNH ĐIỂM NGHẼN ĐỂ DEMO (TRAFFIC VS WEATHER VS ALL)
    # =========================================================================
    if scenario != "Normal" and len(baseline_route) > 3:
        # Xác định 2 vị trí chặng cố định và hoàn toàn khác nhau trên lộ trình
        # legs[0] là chặng Kho (route[0]) -> đơn ưu tiên 001 (route[1]).
        # Giá trị 1 trước đây trỏ nhầm sang chặng 001 -> đơn kế tiếp.
        pos_traffic = 0                                      # Kho -> đơn 001
        pos_weather = max(2, (len(baseline_route) - 2) // 2) # Chặng giữa hành trình (ép tối thiểu chặng 2 để không trùng)

        # Quyết định chặng nào sẽ bị chặn dựa theo kịch bản người dùng chọn
        blocked_positions = []
        if scenario == "Traffic":
            blocked_positions = [pos_traffic]
        elif scenario == "Weather":
            blocked_positions = [pos_weather]
        elif scenario == "Both":
            blocked_positions = [pos_traffic, pos_weather]   # Bật cả 2 chặng cùng lúc

        disruptions = []
        for position in blocked_positions:
            from_index = baseline_route[position]
            to_index = baseline_route[position + 1]
            leg = baseline_optimized_road["legs"][position]
            point = road_routing.canonical_incident_point(leg["geometry"])
            
            # Tách biệt loại sự cố và gán bán kính (clearance) trực quan để làm nổi bật độ nghiêm trọng
            if position == pos_traffic:
                hazard_type = "traffic"
                clearance_val = 150.0  # Kẹt xe: Vòng đỏ nhỏ (150m)
            else:
                hazard_type = "weather"
                clearance_val = 400.0  # Mưa ngập: Vòng đỏ to (400m) để demo ấn tượng

            hazards.append({
                "type": hazard_type,
                "leg_index": position,
                "point": point,
                "from_index": from_index,
                "to_index": to_index,
                "clearance_m": clearance_val, # Gán bán kính an toàn riêng biệt
                "rerouted": True,
            })

            # Phạt ma trận khoảng cách và thời gian di chuyển
            disruptions.append(Bottleneck(
                from_index=from_index,
                to_index=to_index,
                distance_multiplier=1000.0,
                duration_multiplier=1000.0,
                bidirectional=False,
                reason=scenario,
            ))
        # Tại đây hazards luôn chứa đầy đủ các sự cố của scenario đã chọn
        # (Both = Traffic + Weather). Tạo bản sao trước khi lọc reroute_hazards.
        display_hazards = [dict(hazard) for hazard in hazards]

        # Áp dụng hình phạt vào ma trận nền để ép bộ não 2-opt bẻ làn
        active_distance_matrix, active_duration_matrix = apply_penalties(
            road_matrix, duration_matrix, disruptions
        )
        
        # Chạy lại 2-opt định tuyến lại cho các điểm chưa giao
        current_route = reroute_remaining(
            baseline_route,
            completed_leg_count=1,
            penalized_distance_matrix=active_distance_matrix,
        )


    current_route_orders = records_from_route(current_route)
    current_points = [fcfs_points[index] for index in current_route]

    # Dựng geometry theo thứ tự điểm sau khi chạy lại 2-opt
    current_road = road_routing.get_route_legs(current_points)

    if scenario != "Normal" and hazards:
        reroute_hazards = []

        for hazard in hazards:
            blocked_from = hazard["from_index"]
            blocked_to = hazard["to_index"]

            # Tìm xem cặp điểm bị nghẽn (from -> to) hiện tại đang nằm ở vị trí chặng nào 
            # trong lộ trình mới sau khi đã chạy thuật toán 2-opt
            new_leg_index = None
            for index in range(len(current_route) - 1):
                if current_route[index] == blocked_from and current_route[index + 1] == blocked_to:
                    new_leg_index = index
                    break

            # TRƯỜNG HỢP 1: Nếu tuyến sau 2-opt VẪN PHẢI đi qua cặp điểm nghẽn này 
            # (Ví dụ: Chặng từ Kho đến đơn Urgent 001 bắt buộc phải đi vì 001 khóa đầu)
            if new_leg_index is not None:
                reroute_hazards.append({
                    **hazard,
                    "leg_index": new_leg_index, # Gán chính xác vị trí chặng mới để OSRM bẻ làn
                    "clearance_m": hazard.get("clearance_m", 120.0)
                })

        # Nếu cặp điểm nghẽn vẫn tồn tại trong lộ trình mới, gọi OSRM bẻ cong đoạn đó
        if reroute_hazards:
            optimized_road = road_routing.reroute_route_with_hazards(
                current_road,
                reroute_hazards,
            )
            final_clearance = road_routing._minimum_clearance_m(
                optimized_road["geometry"],
                hazards[0]["point"],
            )

            #st.write("Final route clearance:", final_clearance)

            # Không cho UI hiển thị tuyến cũ dưới tên "Reroute".
            if not optimized_road.get("rerouted"):
                failed = [
                    h.get("error", "Không tìm được đường vòng hợp lệ")
                    for h in optimized_road.get("hazards", [])
                    if not h.get("rerouted")
                ]
                st.error(
                    "OSRM không tìm được tuyến né điểm nghẽn: "
                    + "; ".join(failed)
                )
                st.stop()

            # Dùng trạng thái hazard thật do road_routing trả về.
            hazards = optimized_road.get("hazards", reroute_hazards)
        else:
            optimized_road = current_road
    else:
        optimized_road = current_road

    optimized_dist = round(optimized_road["distance_km"], 2)

    # Bước 4: đóng gói khoảng cách từng chặng, chính xác 0.0001 km (10 cm).
    stops = [{
        "order_id": None,
        "customer_id": None,
        "latitude": fcfs["hub"][0],
        "longitude": fcfs["hub"][1],
    }] + fcfs_orders.to_dict("records")
    legs = build_leg_distances(current_route, stops, active_distance_matrix)

    visible_hazards = display_hazards or hazards
    disruption = visible_hazards[0] if visible_hazards else None

    result = {
        "fcfs_distance": fcfs_dist,
        "baseline_distance": baseline_distance,
        "optimized_distance": optimized_dist,
        "fcfs_route_orders": fcfs_orders.to_dict("records"),
        "baseline_route_orders": baseline_route_orders,
        "current_route_orders": current_route_orders,
        "hub": fcfs["hub"],
        "fcfs_road": fcfs_road,
        "baseline_optimized_road": baseline_optimized_road,
        "optimized_road": optimized_road,
        "urgent_order_id": urgent_order_id,
        "scenario": scenario,
        "scenario_disruption": disruption,
        "hazards": visible_hazards,
        "legs": legs,
        "route_indices": current_route,
    }

    result["fcfs_co2"] = calculate_co2(fcfs_dist, DEFAULT_MOTORCYCLE_EMISSION_FACTOR)
    result["optimized_co2"] = calculate_co2(optimized_dist, DEFAULT_MOTORCYCLE_EMISSION_FACTOR)
    result["distance_reduction"] = calculate_reduction_percent(fcfs_dist, optimized_dist)
    result["co2_reduction"] = calculate_reduction_percent(result["fcfs_co2"], result["optimized_co2"])
    result["reroute_below_fcfs"] = optimized_dist < fcfs_dist

    st.session_state["optimization_result"] = result
    st.success("Hệ thống tối ưu hóa hoàn tất dữ liệu hành trình!")

# --- DISPLAY ---
if "optimization_result" in st.session_state:
    result = st.session_state["optimization_result"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Khoảng cách gốc (FCFS)", f"{result['fcfs_distance']:.2f} km")
    m2.metric("Khoảng cách tối ưu / Reroute", f"{result['optimized_distance']:.2f} km", delta=f"-{result['distance_reduction']:.1f}%")
    m3.metric("Khí thải CO₂ gốc (FCFS)", f"{result['fcfs_co2']:.2f} kg")
    m4.metric("Khí thải CO₂ sau tối ưu", f"{result['optimized_co2']:.2f} kg", delta=f"-{result['co2_reduction']:.1f}%")

    st.divider()

    st.subheader("📊 Phân Tích Chỉ Số Thay Đổi Biến Động")
    chart_df = pd.DataFrame({
        "Phương án vận hành": ["FCFS Baseline", "Thuật toán Tối ưu"],
        "Tổng khoảng cách di chuyển (km)": [result["fcfs_distance"], result["optimized_distance"]],
        "Lượng khí thải CO₂ xả thải (kg)": [result["fcfs_co2"], result["optimized_co2"]]
    })
    

    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        # Biểu đồ 1: Tổng khoảng cách di chuyển
        chart1 = alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("Phương án vận hành:N", axis=alt.Axis(labelAngle=0, title=None)), # Khóa góc chữ quay về 0 độ (Nằm ngang)
            y=alt.Y("Tổng khoảng cách di chuyển (km):Q"),
            color=alt.value("#1E3A8A")
        ).properties(height=320)
        st.altair_chart(chart1, use_container_width=True)

    with col_c2:
        # Biểu đồ 2: Lượng khí thải CO2 xả thải
        chart2 = alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("Phương án vận hành:N", axis=alt.Axis(labelAngle=0, title=None)), # Khóa góc chữ quay về 0 độ (Nằm ngang)
            y=alt.Y("Lượng khí thải CO₂ xả thải (kg):Q"),
            color=alt.value("#DC2626")
        ).properties(height=320)
        st.altair_chart(chart2, use_container_width=True)


    st.divider()

    if result.get("scenario") != "Normal":
        st.subheader("🗺️ Bản đồ so sánh phân nhánh độc lập: Tuyến ban đầu vs Tuyến né tránh điểm nghẽn")
        map_col_left, map_col_right = st.columns(2)
        with map_col_left:
            st.markdown("### 🟣 1. Tuyến đường ban đầu (Phát hiện điểm chặn 🚧)")
            st.caption(f"Khoảng cách dự kiến ban đầu: {result['baseline_distance']:.2f} km")
            map_before = build_single_map(
                hub=result["hub"],
                orders=result["baseline_route_orders"],
                road_geometry=result["baseline_optimized_road"]["geometry"] if result.get("baseline_optimized_road") else None,
                color_path=COLOR_BEFORE,
                color_marker=COLOR_BEFORE,
                urgent_id=result["urgent_order_id"],
                disruption=result.get("scenario_disruption"),
                hazards=result.get("hazards", []),
            )
            st.pydeck_chart(map_before, use_container_width=True, height=520, key="map_before_disruption_fixed")
        with map_col_right:
            st.markdown(f"### 🔴 2. Tuyến Reroute thực tế (Né hoàn toàn sự cố: {result['scenario']})")
            st.caption(f"Tổng khoảng cách thực tế sau đi vòng: {result['optimized_distance']:.2f} km")
            map_after = build_single_map(
                hub=result["hub"],
                orders=result["current_route_orders"],
                road_geometry=result["optimized_road"]["geometry"] if result.get("optimized_road") else None,
                color_path=COLOR_AFTER,
                color_marker=COLOR_AFTER,
                urgent_id=result["urgent_order_id"],
                disruption=None,
                hazards=result.get("hazards", []),
                old_geometry=result["baseline_optimized_road"]["geometry"] if result.get("baseline_optimized_road") else None # Đảm bảo dòng này đã được viết chuẩn xác
            )
            st.pydeck_chart(map_after, use_container_width=True, height=520, key="map_after_reroute_fixed")
    else:
        st.subheader("🗺️ Bản đồ so sánh phân nhánh độc lập: FCFS Baseline vs Tuyến tối ưu hóa 2-Opt")
        map_col_left, map_col_right = st.columns(2)
        with map_col_left:
            st.markdown("### 🔵 1. Tuyến đường phân phối FCFS Baseline")
            st.caption(f"Tổng cự ly tuyến đường FCFS: {result['fcfs_distance']:.2f} km")
            map_fcfs = build_single_map(
                hub=result["hub"],
                orders=result["fcfs_route_orders"],
                road_geometry=result["fcfs_road"]["geometry"] if result.get("fcfs_road") else None,
                color_path=COLOR_FCFS,
                color_marker=COLOR_FCFS,
                urgent_id=result["urgent_order_id"],
            )
            st.pydeck_chart(map_fcfs, use_container_width=True, height=520, key="map_fcfs_normal_fixed")
        with map_col_right:
            st.markdown("### 🔴 2. Tuyến đường tối ưu hóa bằng thuật toán 2-Opt")
            st.caption(f"Tổng cự ly tuyến đường tối ưu: {result['optimized_distance']:.2f} km")
            map_opt = build_single_map(
                hub=result["hub"],
                orders=result["current_route_orders"],
                road_geometry=result["optimized_road"]["geometry"], # if result.get("optimized_road") else None
                color_path=COLOR_AFTER,
                color_marker=COLOR_AFTER,
                urgent_id=result["urgent_order_id"],
            )
            st.pydeck_chart(map_opt, use_container_width=True, height=520, key="map_opt_normal_fixed")
