import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from main import EnvironmentalData

st.set_page_config(page_title="Project Okavango", layout="wide")

st.title("Project Okavango")

DISPLAY_TITLES = {
    "land_protected": "Share of Protected Land",
    "annual_deforestation": "Annual Deforestation",
    "mountain_ecosystems": "Protected Mountain Biodiversity",
    "forest_area_change": "Change in Forest Area",
    "land_degraded": "Share of Degraded Land",
}

def pretty_label(indicator_key: str) -> str:
    return DISPLAY_TITLES.get(indicator_key, indicator_key.replace("_", " ").title())

@st.cache_resource
def load_data() -> EnvironmentalData:
    """
    Create the data manager once and reuse it across Streamlit reruns.
    """
    return EnvironmentalData()

data = load_data()

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("Filters")

indicators = data.get_available_indicators()

selected_indicator = st.sidebar.selectbox(
    "Select Indicator",
    indicators,
    format_func=pretty_label
)

# ----------------------------
# YEAR SELECTION
# ----------------------------
years = data.get_available_years(selected_indicator)

if not years:
    st.warning("No years available for this indicator.")
    st.stop()

default_year = max(years)

selected_year = st.sidebar.select_slider(
    "Select Year",
    options=years,
    value=max(years),
)

# ----------------------------
# LOAD DATA FOR CURRENT SELECTION
# ----------------------------

with st.spinner("Loading data..."):
    gdf = data.get_geodata(selected_indicator, selected_year)
    top_bottom_df = data.get_top_bottom(selected_indicator, selected_year)

# ----------------------------
# MAP SECTION
# ----------------------------

# Title for the selected indicator/year
st.subheader(f"{pretty_label(selected_indicator)} ({selected_year})")

# Basic checks so the app doesn't crash
if gdf.empty or selected_indicator not in gdf.columns:
    st.warning("No data available for this selection.")
    st.stop()

if "geometry" not in gdf.columns:
    st.error("Geometry missing.")
    st.stop()

# Pick the ISO-3 id column (to match rows to country shapes)
if "ISO_A3" in gdf.columns:
    id_col = "ISO_A3"
elif "Code" in gdf.columns:
    id_col = "Code"
else:
    st.error("Missing ISO-3 country code column (expected ISO_A3 or Code).")
    st.stop()

# Keep only the columns needed to build the map
map_df = gdf[[id_col, "Entity", selected_indicator, "geometry"]].dropna(subset=[id_col]).copy() 
map_df[selected_indicator] = pd.to_numeric(map_df[selected_indicator], errors="coerce")

# Units shown in the colorbar
UNITS = {
    "land_protected": "%",
    "land_degraded": "%",
    "mountain_ecosystems": "%",
    "annual_deforestation": "ha",
    "forest_area_change": "ha",
}

unit = UNITS.get(selected_indicator, "")
legend_title = f"{pretty_label(selected_indicator)} ({unit})" if unit else pretty_label(selected_indicator)

# Text shown on hover: value + unit, or "No data"
def make_value_text(v):
    if pd.isna(v):
        return "No data"
    return f"{v:.1f}{unit}" if unit else f"{v:.1f}"

map_df["value_text"] = map_df[selected_indicator].apply(make_value_text)

# Convert geometries to GeoJSON so Plotly can draw the country shapes
geojson = json.loads(map_df.to_json())

# Split into missing vs non-missing (so we can color missing values in grey)
missing_df = map_df[map_df[selected_indicator].isna()]
value_df = map_df[map_df[selected_indicator].notna()]

fig_map = go.Figure()

# Layer 1: missing values (grey)
if not missing_df.empty:
    fig_map.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=missing_df[id_col],
            featureidkey=f"properties.{id_col}",
            z=[0] * len(missing_df),  # dummy values just to draw the shapes
            colorscale=[[0, "lightgrey"], [1, "lightgrey"]],
            showscale=False,
            marker_line_color="black",
            marker_line_width=0.6,
            hovertext=missing_df["Entity"],
            customdata=missing_df[["value_text"]],
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                f"{pretty_label(selected_indicator)}: %{{customdata[0]}}"
                "<extra></extra>"
            ),
        )
    )

# Layer 2: real values (viridis)
if not value_df.empty:
    fig_map.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=value_df[id_col],
            featureidkey=f"properties.{id_col}",
            z=value_df[selected_indicator],
            colorscale="Viridis",
            colorbar=dict(title=dict(text=legend_title, side="right"), len=0.9),
            marker_line_color="black",
            marker_line_width=0.6,
            hovertext=value_df["Entity"],
            customdata=value_df[["value_text"]],
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                f"{pretty_label(selected_indicator)}: %{{customdata[0]}}"
                "<extra></extra>"
            ),
        )
    )

# Fit map nicely and remove background/axes
fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))

st.plotly_chart(fig_map, use_container_width=True)
st.caption("Grey countries indicate missing data for the selected indicator and year.")

# ----------------------------
# TOP & BOTTOM SECTION
# ----------------------------

st.subheader("Top 5 and Bottom 5 Countries")

if top_bottom_df.empty:
    st.warning("No ranking data available.")
else:
    fig2, ax2 = plt.subplots(figsize=(10, 5))

    # Sort descending → largest first
    top_bottom_df_sorted = top_bottom_df.sort_values(
        by=selected_indicator,
        ascending=False
    ).reset_index(drop=True)

    # Create color list:
    # First 5 (top performers) → green
    # Last 5 (bottom performers) → red
    colors = ["green"] * 5 + ["red"] * 5

    ax2.barh(
        top_bottom_df_sorted["Entity"],
        top_bottom_df_sorted[selected_indicator],
        color=colors
    )

    # Titles and formatted labels
    ax2.set_title(f"Top & Bottom — {pretty_label(selected_indicator)} ({selected_year})")
    ax2.set_xlabel(pretty_label(selected_indicator))

    # Invert axis so largest appears at top
    ax2.invert_yaxis()

    st.pyplot(fig2)