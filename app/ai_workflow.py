from __future__ import annotations

import html
import math
import unicodedata

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from ollama_utils import (
    DEFAULT_VISION_MODEL,
    assess_environmental_risk_structured,
    describe_image_with_ollama,
    ensure_model,
    find_local_vision_models,
    list_local_models,
    ollama_is_available,
)
from tile_utils import download_satellite_image

try:
    from country_state_city import City, Country, State
except ImportError:
    City = Country = State = None


INDICATOR_LABELS = {
    "annual_deforestation": "Annual deforestation",
    "forest_area_change": "Forest area change",
    "land_degraded": "Land degraded",
    "land_protected": "Land protected",
    "mountain_ecosystems": "Mountain ecosystems",
}

INDICATORS_FOR_CONTEXT = [
    "annual_deforestation",
    "forest_area_change",
    "land_degraded",
    "land_protected",
    "mountain_ecosystems",
]


def render_ai_workflow(data) -> None:
    _render_styles()
    _init_session_state()

    country_options = get_country_names()

    if st.session_state.sync_from_settings:
        sync_inputs_from_settings(country_options)

    with st.sidebar:
        render_sidebar_controls(country_options)

    settings = st.session_state.ai_settings

    st.markdown(
        """
        <div class="okavango-hero">
            <h1>🛰️ AI Workflow</h1>
            <p>Select a location, generate a satellite image, create a factual description, and assess environmental risk.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="view-link-card">
            <div class="view-link-copy">
                Want to go back to the global indicators view? Open the Environmental Explorer.
            </div>
            <a href="?view=explorer" target="_self" class="view-link-btn">Open Environmental Explorer →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">Latitude</div>
                <div class="kpi-value">{settings["latitude"]:.4f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Longitude</div>
                <div class="kpi-value">{settings["longitude"]:.4f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Country</div>
                <div class="kpi-value">{settings["country"]}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">City</div>
                <div class="kpi-value">{settings["city"]}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Selected Area Preview</div>', unsafe_allow_html=True)
    render_location_preview(settings)

    st.markdown('<div class="section-header">Satellite Image</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="satellite-card">
            <div class="satellite-copy">
                Generate a stitched ESRI World Imagery snapshot for the currently selected area.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Generate satellite image", use_container_width=True):
        try:
            with st.spinner("Generating satellite image..."):
                image_path = download_satellite_image(
                    lat=float(settings["latitude"]),
                    lon=float(settings["longitude"]),
                    zoom=int(settings["zoom"]),
                    output_dir="images",
                )
            st.session_state.satellite_image_path = str(image_path)
            st.session_state.satellite_description_result = None
            st.session_state.satellite_analysis_error = None
            reset_risk_outputs()
        except Exception as exc:
            st.session_state.satellite_image_path = None
            st.session_state.satellite_description_result = None
            st.session_state.satellite_analysis_error = str(exc)
            reset_risk_outputs()

    if st.session_state.satellite_analysis_error and not st.session_state.satellite_image_path:
        st.error(f"Could not generate the satellite image: {st.session_state.satellite_analysis_error}")

    if st.session_state.satellite_image_path:
        image_col, analysis_col = st.columns([1.55, 1], gap="large")

        with image_col:
            st.image(
                st.session_state.satellite_image_path,
                caption=(
                    f'{settings["city"]}, {settings["country"]} '
                    f'({settings["latitude"]:.4f}, {settings["longitude"]:.4f})'
                ),
                use_container_width=True,
            )
            st.caption(f"Saved to `{st.session_state.satellite_image_path}`")

        with analysis_col:
            render_description_panel()

    if st.session_state.satellite_description_result:
        result = st.session_state.satellite_description_result

        st.divider()
        st.subheader("Environmental risk")

        st.markdown(
            """
            <div class="risk-window-intro">
                This assessment combines local visual evidence from the image description with country-level historical indicator context from the five environmental datasets.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Assess environmental risk", use_container_width=True):
            status_box = st.empty()
            try:
                status_box.info("Building dataset context...")
                dataset_context, snapshots = build_dataset_context(
                    data,
                    st.session_state.ai_settings["country"],
                )

                status_box.info("Running structured risk assessment with Ollama...")
                model_result = assess_environmental_risk_structured(
                    image_description=result["description"],
                    dataset_context=dataset_context,
                    model_name=st.session_state.selected_vision_model,
                    auto_pull_model=True,
                )

                dataset_score, dataset_reason = compute_dataset_risk_score(snapshots)
                combined = combine_risk_scores(model_result, dataset_score, dataset_reason)

                st.session_state.risk_result = combined
                st.session_state.risk_snapshots = snapshots
                st.session_state.risk_context_text = dataset_context
                st.session_state.satellite_analysis_error = None
                status_box.success("Risk assessment finished.")
            except Exception as exc:
                st.session_state.risk_result = None
                st.session_state.risk_snapshots = []
                st.session_state.risk_context_text = ""
                st.session_state.satellite_analysis_error = str(exc)
                status_box.empty()

        if st.session_state.satellite_analysis_error and not st.session_state.risk_result:
            st.error(f"Could not assess environmental risk: {st.session_state.satellite_analysis_error}")

        if st.session_state.risk_result:
            render_risk_window(
                st.session_state.risk_result,
                st.session_state.risk_snapshots,
            )


def render_description_panel() -> None:
    st.markdown("#### Image description")
    st.caption("Run a local Ollama vision model on the generated satellite image.")

    if not ollama_is_available():
        st.warning("Ollama is not reachable. Start the Ollama app first.")
        st.code("ollama serve", language="bash")
        return

    local_models = list_local_models()
    if not local_models:
        st.warning("No local Ollama models were found.")
        st.code("ollama pull llava:7b", language="bash")
        return

    selected_model = st.session_state.selected_vision_model

    if st.button("Describe image with Ollama", use_container_width=True):
        status_box = st.empty()
        try:
            status_box.info("Preparing image for Ollama...")
            ensure_model(selected_model, auto_pull=True)

            status_box.info("Running local vision model... this can take a while on slower devices.")
            result = describe_image_with_ollama(
                image_path=st.session_state.satellite_image_path,
                model_name=selected_model,
                max_size=int(st.session_state.ollama_image_size),
                quality=80,
                timeout=240,
                auto_pull_model=True,
            )

            st.session_state.satellite_description_result = result
            st.session_state.satellite_analysis_error = None
            reset_risk_outputs()
            status_box.success("Description finished.")
        except Exception as exc:
            st.session_state.satellite_description_result = None
            st.session_state.satellite_analysis_error = str(exc)
            reset_risk_outputs()
            status_box.error(f"Description failed: {exc}")

    if st.session_state.satellite_analysis_error and not st.session_state.satellite_description_result:
        st.error(f"Could not describe the satellite image: {st.session_state.satellite_analysis_error}")
        return

    if not st.session_state.satellite_description_result:
        st.info("Click the button to generate a description.")
        return

    result = st.session_state.satellite_description_result
    st.write(result["description"])
    st.caption(f"Model: `{result['model_name']}`")
    st.caption(f"Runtime: `{result['elapsed_seconds']}` seconds")
    st.caption(f"Prepared image: `{result['prepared_image_path']}`")


def render_location_preview(settings: dict) -> None:
    preview_df = pd.DataFrame(
        {"lat": [settings["latitude"]], "lon": [settings["longitude"]]}
    )

    view_state = pdk.ViewState(
        latitude=settings["latitude"],
        longitude=settings["longitude"],
        zoom=settings["zoom"],
        pitch=0,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=preview_df,
        get_position="[lon, lat]",
        get_radius=120,
        get_fill_color=[214, 76, 76, 180],
        pickable=True,
    )

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": f'{settings["city"]}, {settings["country"]}'},
    )

    st.pydeck_chart(deck, use_container_width=True)


def render_sidebar_controls(country_options: list[str]) -> None:
    st.markdown("### 🛰️ AI controls")
    st.markdown("##### Location method")

    is_coordinates = st.session_state.location_mode == "By coordinates"
    is_country_city = st.session_state.location_mode == "By country and city"

    st.markdown(
        f"""
        <style>
        div[data-testid="stButton"][data-key="mode_coordinates"] button,
        div.st-key-mode_coordinates button {{
            width: 100% !important;
            border-radius: 12px !important;
            min-height: 3rem !important;
            border: {"2px solid #000000" if is_coordinates else "1px solid #d8d5ce"} !important;
            background: #ffffff !important;
            color: #1a1a18 !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            box-shadow: none !important;
            outline: none !important;
            margin-bottom: 0.4rem !important;
        }}

        div[data-testid="stButton"][data-key="mode_country_city"] button,
        div.st-key-mode_country_city button {{
            width: 100% !important;
            border-radius: 12px !important;
            min-height: 3rem !important;
            border: {"2px solid #000000" if is_country_city else "1px solid #d8d5ce"} !important;
            background: #ffffff !important;
            color: #1a1a18 !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            box-shadow: none !important;
            outline: none !important;
            margin-bottom: 0.4rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("📍 Coordinates", key="mode_coordinates", use_container_width=True):
        st.session_state.location_mode = "By coordinates"
        st.rerun()

    if st.button("🌍 Country · Region · City", key="mode_country_city", use_container_width=True):
        st.session_state.location_mode = "By country and city"
        st.rerun()

    previous_zoom = int(st.session_state.ai_settings["zoom"])
    current_zoom = st.slider("Zoom", min_value=1, max_value=20, key="zoom_input")

    if current_zoom != previous_zoom:
        st.session_state.ai_settings["zoom"] = int(current_zoom)
        reset_generated_outputs()

    if st.session_state.location_mode == "By coordinates":
        render_coordinate_selector()
    else:
        render_place_selector(country_options)

    st.divider()
    st.markdown("##### Ollama settings")

    if ollama_is_available():
        vision_models = find_local_vision_models()
        all_local_models = list_local_models()
        candidate_models = vision_models if vision_models else all_local_models

        if not candidate_models:
            candidate_models = [DEFAULT_VISION_MODEL]

        if st.session_state.selected_vision_model not in candidate_models:
            st.session_state.selected_vision_model = candidate_models[0]

        st.selectbox(
            "Vision model",
            options=candidate_models,
            key="selected_vision_model",
            help="Choose a locally installed Ollama model.",
        )

        st.slider(
            "Prepared image size",
            min_value=384,
            max_value=1280,
            value=st.session_state.ollama_image_size,
            step=128,
            key="ollama_image_size",
            help="Smaller images are usually much faster on slower devices.",
        )

        st.caption("Tip: 512 or 768 is usually much lighter than sending the full image.")
    else:
        st.caption("Start Ollama to load local models.")


def render_coordinate_selector() -> None:
    try:
        lat_default = float(str(st.session_state.lat_input).replace(",", "."))
    except Exception:
        lat_default = float(st.session_state.ai_settings["latitude"])

    try:
        lon_default = float(str(st.session_state.lon_input).replace(",", "."))
    except Exception:
        lon_default = float(st.session_state.ai_settings["longitude"])

    latitude_value = st.number_input(
        "Latitude",
        min_value=-90.0,
        max_value=90.0,
        value=lat_default,
        step=0.0001,
        format="%.4f",
        help="Value between -90 and 90",
    )

    longitude_value = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=lon_default,
        step=0.0001,
        format="%.4f",
        help="Value between -180 and 180",
    )

    st.session_state.lat_input = f"{latitude_value:.4f}"
    st.session_state.lon_input = f"{longitude_value:.4f}"

    st.caption("Enter exact coordinates to preview a specific location.")

    if st.button("Save coordinates", use_container_width=True):
        country, city = reverse_geocode(latitude_value, longitude_value)
        st.session_state.ai_settings = {
            "latitude": latitude_value,
            "longitude": longitude_value,
            "zoom": int(st.session_state.zoom_input),
            "country": country,
            "region": "",
            "city": city,
        }
        reset_generated_outputs()
        st.session_state.sync_from_settings = True
        st.rerun()


def render_place_selector(country_options: list[str]) -> None:
    selected_country = st.selectbox(
        "Country",
        options=country_options,
        key="place_country",
    )

    region_options = get_region_names(selected_country)
    if region_options:
        region_choices = [""] + region_options
        if st.session_state.place_region not in region_choices:
            st.session_state.place_region = ""

        selected_region = st.selectbox(
            "Region",
            options=region_choices,
            key="place_region",
            format_func=lambda region: region if region else "All regions (optional)",
        )
    else:
        selected_region = ""
        st.session_state.place_region = ""
        st.selectbox("Region", options=["No region filter needed"], disabled=True)

    city_options = get_city_names(selected_country, selected_region)
    if city_options:
        if st.session_state.place_city not in city_options:
            st.session_state.place_city = city_options[0]
        selected_city = st.selectbox("City", options=city_options, key="place_city")
    else:
        selected_city = ""
        st.selectbox("City", options=["No cities found"], disabled=True)

    st.caption("Choose a country, optionally filter by region, and then choose a city.")

    preview_lat, preview_lon = (None, None)
    if selected_country and selected_city:
        preview_lat, preview_lon = geocode_place(selected_country, selected_region, selected_city)

    if st.button("Use selected place", use_container_width=True):
        if preview_lat is None or preview_lon is None:
            st.error("Could not find coordinates for the selected location.")
            return

        st.session_state.ai_settings = {
            "latitude": preview_lat,
            "longitude": preview_lon,
            "zoom": int(st.session_state.zoom_input),
            "country": selected_country,
            "region": selected_region,
            "city": selected_city,
        }
        reset_generated_outputs()
        st.session_state.sync_from_settings = True
        st.rerun()


def render_risk_window(risk_result: dict, snapshots: list[dict]) -> None:
    final_label = risk_result["overall_risk"]["label"]
    final_score = risk_result["overall_risk"]["score"]
    visual_score = risk_result["overall_visual_risk"]["level"]
    dataset_score = risk_result["dataset_context_risk"]["level"]

    st.markdown(
        """
        <div class="risk-window-card">
            <div class="risk-window-title">Environmental Risk Window</div>
            <div class="risk-window-sub">
                The final result combines image-based evidence and broader country-level dataset context.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    badge_col, visual_col, dataset_col = st.columns(3)

    with badge_col:
        render_overall_risk_badge(final_label, final_score)

    with visual_col:
        st.metric("Visual risk score", f"{visual_score:.2f}")
        st.caption("Derived from the structured Ollama assessment.")

    with dataset_col:
        st.metric("Dataset context score", f"{dataset_score:.2f}")
        st.caption("Derived from historical indicator snapshots and trends.")

    st.markdown("### Risk traffic light")
    render_risk_traffic_light(final_label)

    left, right = st.columns([1.05, 1.15], gap="large")

    with left:
        st.markdown("#### Final reasoning")
        st.write(risk_result["overall_risk"]["reason"])

        st.markdown("#### Visual risk dimensions")
        render_dimension_table(risk_result)

    with right:
        st.markdown(f"#### Dataset trend context of {st.session_state.ai_settings['country']}")
        render_dataset_snapshot_cards(snapshots)

    st.markdown('<div class="technical-context-gap"></div>', unsafe_allow_html=True)
    with st.expander("Show technical context used for the model"):
        st.code(st.session_state.risk_context_text, language="text")


def render_overall_risk_badge(label: str, score: float) -> None:
    label = label.upper()

    if label == "HIGH":
        st.error(f"High risk · score {score:.2f}")
    elif label == "MODERATE":
        st.warning(f"Moderate risk · score {score:.2f}")
    else:
        st.success(f"Low risk · score {score:.2f}")


def render_risk_traffic_light(label: str) -> None:
    active = label.upper()

    def block(text: str, is_active: bool, color: str) -> str:
        border = "3px solid #1a1a18" if is_active else "1px solid #d8d5ce"
        opacity = "1" if is_active else "0.45"
        return (
            f'<div style="flex:1; background:{color}; border:{border}; border-radius:10px; '
            f'padding:0.9rem 0.8rem; text-align:center; font-weight:700; color:#1a1a18; opacity:{opacity};">'
            f"{text}</div>"
        )

    st.markdown(
        (
            '<div style="display:flex; gap:0.8rem; margin-bottom:1rem;">'
            + block("LOW", active == "LOW", "#dff3e5")
            + block("MODERATE", active == "MODERATE", "#fff0c7")
            + block("HIGH", active == "HIGH", "#f9d4d4")
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_dimension_table(risk_result: dict) -> None:
    rows = [
        ("Deforestation", risk_result["deforestation_risk"]["level"], risk_result["deforestation_risk"]["reason"]),
        ("Degradation", risk_result["degradation_risk"]["level"], risk_result["degradation_risk"]["reason"]),
        ("Fire", risk_result["fire_risk"]["level"], risk_result["fire_risk"]["reason"]),
        ("Flood", risk_result["flood_risk"]["level"], risk_result["flood_risk"]["reason"]),
        ("Fragmentation", risk_result["fragmentation_risk"]["level"], risk_result["fragmentation_risk"]["reason"]),
    ]

    body_rows = []
    for dimension, level, reason in rows:
        reason_text = str(reason).strip() or "No reason provided."
        body_rows.append(
            (
                '<div class="risk-grid-row">'
                '<div class="risk-grid-cell risk-grid-dimension">{dimension}</div>'
                '<div class="risk-grid-cell risk-grid-level-cell"><span class="risk-level-pill">{level}</span></div>'
                '<div class="risk-grid-cell risk-grid-reason">{reason}</div>'
                "</div>"
            ).format(
                dimension=html.escape(str(dimension)),
                level=html.escape(f"{float(level):.1f}"),
                reason=html.escape(reason_text),
            )
        )

    st.markdown(
        (
            '<div class="risk-grid-table">'
            '<div class="risk-grid risk-grid-header-row">'
            '<div class="risk-grid-header">Dimension</div>'
            '<div class="risk-grid-header">Level</div>'
            '<div class="risk-grid-header">Reason</div>'
            '</div>'
            '{rows}'
            '</div>'
        ).format(rows="".join(body_rows)),
        unsafe_allow_html=True,
    )


def render_dataset_snapshot_cards(snapshots: list[dict]) -> None:
    if not snapshots:
        st.info("No dataset context available for this country.")
        return

    for index in range(0, len(snapshots), 2):
        cols = st.columns(2, gap="medium")

        for col, snap in zip(cols, snapshots[index:index + 2]):
            with col:
                label = html.escape(str(snap["label"]))

                if snap.get("missing", False) or snap.get("latest_value") is None:
                    st.markdown(
                        (
                            '<div class="dataset-context-card">'
                            f'<div class="dataset-context-label">{label}</div>'
                            '<div class="dataset-context-value">No data available</div>'
                            '<div class="dataset-context-meta">Year: -</div>'
                            '<div class="dataset-context-badge is-missing">No data</div>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    continue

                delta = snap["trend_delta"]
                direction = interpret_trend_direction(snap["indicator"], delta)
                badge_class = {
                    "improving": "is-improving",
                    "worsening": "is-worsening",
                    "stable": "is-stable",
                }.get(direction, "is-stable")
                delta_class = {
                    "improving": "is-improving",
                    "worsening": "is-worsening",
                    "stable": "is-stable",
                }.get(direction, "is-stable")

                st.markdown(
                    (
                        '<div class="dataset-context-card">'
                        f'<div class="dataset-context-label">{label}</div>'
                        f'<div class="dataset-context-value">{html.escape("{:.2f}".format(snap["latest_value"]))}</div>'
                        f'<div class="dataset-context-delta {delta_class}">{html.escape(f"{delta:+.2f}")}</div>'
                        f'<div class="dataset-context-meta">Year: {html.escape(str(snap["latest_year"]))}</div>'
                        f'<div class="dataset-context-badge {badge_class}">{html.escape(direction.title())}</div>'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )


def interpret_trend_direction(indicator: str, delta: float) -> str:
    higher_is_worse = indicator in {
        "annual_deforestation",
        "land_degraded",
    }
    lower_is_worse = indicator in {
        "forest_area_change",
        "land_protected",
        "mountain_ecosystems",
    }

    if math.isclose(delta, 0.0, abs_tol=1e-9):
        return "stable"

    if higher_is_worse:
        return "worsening" if delta > 0 else "improving"

    if lower_is_worse:
        return "worsening" if delta < 0 else "improving"

    return "changing"


def _find_country_name_column(gdf) -> str | None:
    for col in ["ADMIN", "name", "NAME", "Entity"]:
        if col in gdf.columns:
            return col
    return None


def get_country_indicator_snapshot(data, country_name: str, indicator: str) -> dict | None:
    years = data.get_available_years(indicator)
    if not years:
        return None

    records = []

    for year in years:
        gdf = data.get_geodata(indicator, year)
        name_col = _find_country_name_column(gdf)

        if name_col is None or indicator not in gdf.columns:
            continue

        dataset_country_name = resolve_country_in_dataframe(country_name, gdf[name_col])
        if dataset_country_name is None:
            continue

        row = gdf[gdf[name_col].astype(str) == dataset_country_name]
        if row.empty:
            continue

        value = row.iloc[0][indicator]
        if pd.isna(value):
            continue

        all_values = gdf[indicator].dropna()
        percentile = None
        if len(all_values) > 0:
            percentile = float((all_values <= value).mean() * 100)

        records.append(
            {
                "year": int(year),
                "value": float(value),
                "percentile": percentile,
            }
        )

    if not records:
        return None

    records = sorted(records, key=lambda x: x["year"])
    latest = records[-1]
    recent = records[-5:] if len(records) >= 5 else records
    trend_delta = recent[-1]["value"] - recent[0]["value"] if len(recent) > 1 else 0.0

    return {
        "indicator": indicator,
        "label": INDICATOR_LABELS[indicator],
        "latest_year": latest["year"],
        "latest_value": latest["value"],
        "latest_percentile": latest["percentile"],
        "trend_delta": trend_delta,
        "series": records,
    }


def build_dataset_context(data, country_name: str) -> tuple[str, list[dict]]:
    snapshots = []
    lines = [f"Country: {country_name}"]

    for indicator in INDICATORS_FOR_CONTEXT:
        snapshot = get_country_indicator_snapshot(data, country_name, indicator)

        if snapshot is None:
            snapshots.append(
                {
                    "indicator": indicator,
                    "label": INDICATOR_LABELS[indicator],
                    "latest_year": None,
                    "latest_value": None,
                    "latest_percentile": None,
                    "trend_delta": None,
                    "series": [],
                    "missing": True,
                }
            )
            lines.append(f"- {INDICATOR_LABELS[indicator]}: no data available")
            continue

        snapshot["missing"] = False
        snapshots.append(snapshot)

        value = snapshot["latest_value"]
        year = snapshot["latest_year"]
        delta = snapshot["trend_delta"]
        pct = snapshot["latest_percentile"]
        pct_text = f"{pct:.1f}" if pct is not None else "n/a"

        lines.append(
            f"- {snapshot['label']}: latest={value:.2f} in {year}, "
            f"5-year trend delta={delta:+.2f}, "
            f"percentile_vs_countries={pct_text}"
        )

    return "\n".join(lines), snapshots


def compute_dataset_risk_score(snapshots: list[dict]) -> tuple[float, str]:
    if not snapshots:
        return 0.0, "No dataset context was available for the selected country."

    score_parts = []
    reasons = []

    for snap in snapshots:
        if not snap:
            continue

        indicator = snap["indicator"]
        pct = snap.get("latest_percentile")
        delta = snap.get("trend_delta", 0.0)
        latest_value = snap.get("latest_value")

        sev = 0.0

        if latest_value is None:
            continue

        if pct is not None:
            if indicator in {"annual_deforestation", "land_degraded"}:
                if pct >= 80:
                    sev += 1.2
                elif pct >= 60:
                    sev += 0.7

            elif indicator in {"land_protected", "mountain_ecosystems"}:
                if pct <= 20:
                    sev += 1.0
                elif pct <= 40:
                    sev += 0.5

            elif indicator == "forest_area_change":
                if latest_value < 0:
                    sev += 0.8
                if pct <= 20:
                    sev += 0.4

        worsening = False
        if indicator in {"annual_deforestation", "land_degraded"} and delta > 0:
            worsening = True
        elif indicator in {"forest_area_change", "land_protected", "mountain_ecosystems"} and delta < 0:
            worsening = True

        if worsening:
            sev += 0.4

        sev = min(sev, 2.0)
        score_parts.append(sev)

        if sev >= 1.0:
            reasons.append(f"{snap['label']} suggests elevated concern.")
        elif sev >= 0.5:
            reasons.append(f"{snap['label']} adds moderate context risk.")

    if not score_parts:
        return 0.0, "Some indicators were missing, and the available dataset context did not indicate elevated concern."

    score = round(sum(score_parts) / len(score_parts), 2)

    if not reasons:
        reasons.append("The available historical indicators do not strongly signal risk.")

    return score, " ".join(reasons)


def combine_risk_scores(model_result: dict, dataset_score: float, dataset_reason: str) -> dict:
    visual_score = float(model_result["overall_visual_risk"]["level"])
    final_score = round(0.6 * visual_score + 0.4 * dataset_score, 2)

    if final_score >= 1.4:
        final_label = "HIGH"
    elif final_score >= 0.75:
        final_label = "MODERATE"
    else:
        final_label = "LOW"

    final_reason = (
        f"Visual evidence was assessed as {model_result['overall_visual_risk']['label']}. "
        f"Dataset context score was {dataset_score:.2f}. "
        f"{model_result['overall_visual_risk']['reason']} "
        f"{dataset_reason}"
    ).strip()

    return {
        **model_result,
        "dataset_context_risk": {
            "level": dataset_score,
            "reason": dataset_reason,
        },
        "overall_risk": {
            "score": final_score,
            "label": final_label,
            "reason": final_reason,
        },
    }


def reset_generated_outputs() -> None:
    st.session_state.satellite_image_path = None
    st.session_state.satellite_description_result = None
    st.session_state.satellite_analysis_error = None
    reset_risk_outputs()


def reset_risk_outputs() -> None:
    st.session_state.risk_result = None
    st.session_state.risk_snapshots = []
    st.session_state.risk_context_text = ""


def _render_styles() -> None:
    st.markdown(
        """
        <style>
            .okavango-hero {
                background-color: #ffffff;
                border-radius: 12px;
                padding: 2rem 2.5rem;
                margin-bottom: 1.5rem;
                border: 0.5px solid #e0ddd6;
                border-left: 3px solid #2d6a4f;
            }

            .okavango-hero h1 {
                font-family: 'Lora', serif;
                font-size: 2.2rem;
                color: #1a1a18;
                margin: 0 0 0.3rem 0;
                letter-spacing: -0.3px;
            }

            .okavango-hero p {
                color: #888880;
                font-size: 0.95rem;
                font-weight: 300;
                margin: 0;
            }

            .kpi-row {
                display: flex;
                gap: 1rem;
                margin-bottom: 1.5rem;
            }

            .kpi-card {
                flex: 1;
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 10px;
                padding: 1rem 1.2rem;
            }

            .kpi-label {
                font-size: 0.7rem;
                font-weight: 500;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #888880;
                margin-bottom: 0.5rem;
            }

            .kpi-value {
                font-family: 'Lora', serif;
                font-size: 1.5rem;
                color: #1a1a18;
                line-height: 1.1;
                word-break: break-word;
            }

            .section-header {
                font-family: 'Lora', serif;
                font-size: 1.2rem;
                color: #1a1a18;
                border-bottom: 0.5px solid #e0ddd6;
                padding-bottom: 0.5rem;
                margin-bottom: 1rem;
            }

            .view-link-card {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 10px;
                padding: 1rem 1.2rem;
                margin: 0.25rem 0 1.25rem 0;
            }

            .view-link-copy {
                color: #66665f;
                font-size: 0.95rem;
                line-height: 1.5;
            }

            .risk-grid-table {
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                overflow: hidden;
                background: #ffffff;
            }

            .risk-grid {
                display: grid;
                grid-template-columns: 1.15fr 0.7fr 3.05fr;
                background: #f7f7f5;
            }

            .risk-grid-header {
                padding: 0.95rem 1rem;
                color: #66665f;
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                border-right: 0.5px solid #e0ddd6;
            }

            .risk-grid-header:last-child {
                border-right: none;
            }

            .risk-grid-row {
                display: grid;
                grid-template-columns: 1.15fr 0.7fr 3.05fr;
                background: #ffffff;
            }

            .risk-grid-cell {
                background: #ffffff;
                border-bottom: 0.5px solid #e0ddd6;
                border-right: 0.5px solid #e0ddd6;
                padding: 1rem;
                color: #1f1f1c;
                font-size: 0.94rem;
                line-height: 1.55;
                min-height: 100%;
            }

            .risk-grid-row .risk-grid-cell:last-child {
                border-right: none;
            }

            .risk-grid-table .risk-grid-row:last-child .risk-grid-cell {
                border-bottom: none;
            }

            .risk-grid-dimension {
                font-weight: 500;
            }

            .risk-grid-level-cell {
                display: flex;
                align-items: center;
            }

            .risk-grid-reason {
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .risk-level-pill {
                display: inline-block;
                min-width: 2.3rem;
                padding: 0.2rem 0.55rem;
                border-radius: 999px;
                background: #f1efe9;
                border: 1px solid #ddd8cf;
                font-weight: 700;
                text-align: center;
            }

            .technical-context-gap {
                height: 1.25rem;
            }

            .view-link-btn {
                display: inline-block;
                text-decoration: none !important;
                background: #2d6a4f;
                color: white !important;
                padding: 0.7rem 1rem;
                border-radius: 8px;
                font-weight: 600;
                white-space: nowrap;
            }

            .satellite-card {
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                padding: 1.2rem;
                margin-top: 1.25rem;
            }

            .satellite-copy {
                color: #66665f;
                font-size: 0.95rem;
                line-height: 1.5;
                margin-bottom: 0.9rem;
            }

            .analysis-panel {
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                padding: 1.2rem;
                min-height: 100%;
            }

            .analysis-intro {
                color: #66665f;
                font-size: 0.95rem;
                line-height: 1.5;
                margin-bottom: 1rem;
            }

            .risk-window-intro {
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                padding: 1rem 1.1rem;
                color: #66665f;
                margin-bottom: 1rem;
            }

            .risk-window-card {
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                padding: 1.2rem;
                margin-bottom: 1rem;
            }

            .risk-window-title {
                font-family: 'Lora', serif;
                font-size: 1.3rem;
                color: #1a1a18;
                margin-bottom: 0.2rem;
            }

            .risk-window-sub {
                color: #66665f;
                font-size: 0.95rem;
                line-height: 1.5;
            }

            .dataset-context-card {
                background: #ffffff;
                border: 0.5px solid #e0ddd6;
                border-radius: 12px;
                padding: 0.95rem 1rem;
                margin-bottom: 0.8rem;
                min-height: 12.2rem;
            }

            .dataset-context-label {
                color: #66665f;
                font-size: 0.82rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin-bottom: 0.45rem;
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .dataset-context-value {
                color: #1f1f1c;
                font-family: 'Lora', serif;
                font-size: 1.55rem;
                line-height: 1.1;
                margin-bottom: 0.35rem;
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .dataset-context-delta {
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 0.2rem;
            }

            .dataset-context-delta.is-improving {
                color: #1f6b3a;
            }

            .dataset-context-delta.is-worsening {
                color: #a23d3d;
            }

            .dataset-context-delta.is-stable {
                color: #1f1f1c;
            }

            .dataset-context-meta {
                color: #7a7872;
                font-size: 0.95rem;
                margin-bottom: 0.45rem;
            }

            .dataset-context-badge {
                display: inline-block;
                padding: 0.35rem 0.7rem;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
                border: 1px solid transparent;
                margin-top: 0.2rem;
                align-self: flex-start;
            }

            .dataset-context-badge.is-improving {
                background: #dff3e5;
                border-color: #bddfc7;
                color: #1f6b3a;
            }

            .dataset-context-badge.is-worsening {
                background: #f9d4d4;
                border-color: #eab5b5;
                color: #a23d3d;
            }

            .dataset-context-badge.is-stable,
            .dataset-context-badge.is-missing {
                background: #f1efe9;
                border-color: #ddd8cf;
                color: #66665f;
            }

            div[data-testid="stNumberInput"] input {
                background-color: #fcfcfa !important;
                border: 1px solid #d8d5ce !important;
                border-radius: 10px !important;
                color: #1a1a18 !important;
            }

            div[data-testid="stNumberInput"] label {
                color: #888880 !important;
                font-size: 0.72rem !important;
                font-weight: 500 !important;
                letter-spacing: 0.08em !important;
                text-transform: uppercase !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    if "ai_settings" not in st.session_state:
        st.session_state.ai_settings = {
            "latitude": -18.9249,
            "longitude": 47.5213,
            "zoom": 12,
            "country": "Madagascar",
            "region": "",
            "city": "Antananarivo",
        }

    if "location_mode" not in st.session_state:
        st.session_state.location_mode = "By coordinates"

    if "lat_input" not in st.session_state:
        st.session_state.lat_input = f"{st.session_state.ai_settings['latitude']:.4f}"

    if "lon_input" not in st.session_state:
        st.session_state.lon_input = f"{st.session_state.ai_settings['longitude']:.4f}"

    if "zoom_input" not in st.session_state:
        st.session_state.zoom_input = int(st.session_state.ai_settings["zoom"])

    if "place_country" not in st.session_state:
        st.session_state.place_country = st.session_state.ai_settings["country"]

    if "place_region" not in st.session_state:
        st.session_state.place_region = st.session_state.ai_settings.get("region", "")

    if "place_city" not in st.session_state:
        st.session_state.place_city = st.session_state.ai_settings["city"]

    if "satellite_image_path" not in st.session_state:
        st.session_state.satellite_image_path = None

    if "satellite_description_result" not in st.session_state:
        st.session_state.satellite_description_result = None

    if "satellite_analysis_error" not in st.session_state:
        st.session_state.satellite_analysis_error = None

    if "sync_from_settings" not in st.session_state:
        st.session_state.sync_from_settings = True

    if "selected_vision_model" not in st.session_state:
        st.session_state.selected_vision_model = DEFAULT_VISION_MODEL

    if "ollama_image_size" not in st.session_state:
        st.session_state.ollama_image_size = 768

    if "risk_result" not in st.session_state:
        st.session_state.risk_result = None

    if "risk_snapshots" not in st.session_state:
        st.session_state.risk_snapshots = []

    if "risk_context_text" not in st.session_state:
        st.session_state.risk_context_text = ""


def sync_inputs_from_settings(country_options: list[str]) -> None:
    settings = st.session_state.ai_settings

    st.session_state.lat_input = f"{settings['latitude']:.4f}"
    st.session_state.lon_input = f"{settings['longitude']:.4f}"
    st.session_state.zoom_input = int(settings["zoom"])

    default_country = settings["country"]
    if default_country not in country_options:
        default_country = country_options[0] if country_options else "Portugal"
    st.session_state.place_country = default_country

    region_options_init = get_region_names(default_country)
    default_region = settings.get("region", "")
    if default_region not in region_options_init:
        default_region = region_options_init[0] if region_options_init else ""
    st.session_state.place_region = default_region

    city_options_init = get_city_names(default_country, default_region)
    default_city = settings.get("city", "")
    if default_city not in city_options_init:
        default_city = city_options_init[0] if city_options_init else ""
    st.session_state.place_city = default_city

    st.session_state.sync_from_settings = False


def ascii_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = " ".join(text.split())
    return text.strip()


def safe_text(text: str, fallback: str = "Unknown") -> str:
    cleaned = ascii_text(text)
    return cleaned if cleaned else fallback

def normalize_text(text: str) -> str:
    return safe_text(text, fallback="").lower().replace("&", "and").strip()


def resolve_country_in_dataframe(country_name: str, country_series: pd.Series) -> str | None:
    target = normalize_text(country_name)

    raw_names = country_series.dropna().astype(str).unique().tolist()
    normalized_map = {normalize_text(name): name for name in raw_names}

    if target in normalized_map:
        return normalized_map[target]

    contains_matches = [
        original
        for norm, original in normalized_map.items()
        if target in norm or norm in target
    ]
    if contains_matches:
        return contains_matches[0]

    return None

@st.cache_data(show_spinner=False)
def get_country_names() -> list[str]:
    if Country is None:
        return ["Portugal"]
    try:
        countries = Country.get_countries()
        names = sorted(
            [safe_text(c.name, fallback="") for c in countries if safe_text(c.name, fallback="")]
        )
        return names if names else ["Portugal"]
    except Exception:
        return ["Portugal"]


@st.cache_data(show_spinner=False)
def get_country_code(country_name: str):
    if Country is None:
        return None
    try:
        for country in Country.get_countries():
            if safe_text(country.name, fallback="") == country_name:
                return country.iso2
    except Exception:
        return None
    return None


@st.cache_data(show_spinner=False)
def get_region_names(country_name: str) -> list[str]:
    if State is None:
        return []
    country_code = get_country_code(country_name)
    if not country_code:
        return []
    try:
        states = State.get_states_of_country(country_code)
        return sorted(
            [safe_text(s.name, fallback="") for s in states if safe_text(s.name, fallback="")]
        )
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def get_region_code(country_name: str, region_name: str):
    if State is None:
        return None
    country_code = get_country_code(country_name)
    if not country_code:
        return None
    try:
        for state in State.get_states_of_country(country_code):
            if safe_text(state.name, fallback="") == region_name:
                return state.iso_code
    except Exception:
        return None
    return None


@st.cache_data(show_spinner=False)
def get_city_names(country_name: str, region_name: str = "") -> list[str]:
    if City is None:
        return []
    country_code = get_country_code(country_name)
    if not country_code:
        return []

    def normalize_city_names(cities) -> list[str]:
        names = []
        seen = set()
        for city in cities:
            name = safe_text(city.name, fallback="")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return sorted(names)

    if region_name:
        region_code = get_region_code(country_name, region_name)
        if not region_code:
            return []
        try:
            cities = City.get_cities_of_state(country_code, region_code)
            return normalize_city_names(cities)
        except Exception:
            return []

    try:
        if hasattr(City, "get_cities_of_country"):
            cities = City.get_cities_of_country(country_code)
            return normalize_city_names(cities)
    except Exception:
        pass

    if State is None:
        return []

    try:
        all_cities = []
        for state in State.get_states_of_country(country_code):
            region_code = getattr(state, "iso_code", None)
            if not region_code:
                continue
            try:
                all_cities.extend(City.get_cities_of_state(country_code, region_code))
            except Exception:
                continue
        return normalize_city_names(all_cities)
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def geocode_place(country: str, region: str, city: str) -> tuple[float | None, float | None]:
    query_parts = [city.strip(), region.strip(), country.strip()]
    query = ", ".join(part for part in query_parts if part)
    if not query:
        return None, None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "accept-language": "en",
    }
    headers = {
        "User-Agent": "ProjectOkavango/1.0 (student project)",
        "Accept-Language": "en",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        if not results:
            return None, None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        return None, None


@st.cache_data(show_spinner=False)
def reverse_geocode(lat: float, lon: float) -> tuple[str, str]:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 10,
        "accept-language": "en",
    }
    headers = {
        "User-Agent": "ProjectOkavango/1.0 (student project)",
        "Accept-Language": "en",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        country = safe_text(address.get("country", ""), fallback="Unknown")
        city = safe_text(
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
            or "",
            fallback="Unknown",
        )
        return country, city
    except Exception:
        return "Unknown", "Unknown"
