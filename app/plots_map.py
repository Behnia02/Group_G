# Builds the Plotly choropleth map figure for the Streamlit app

import json
import pandas as pd
import plotly.graph_objects as go


# Titles used for UI and legends
DISPLAY_TITLES = {
    "land_protected": "Share of Protected Land",
    "annual_deforestation": "Annual Deforestation",
    "mountain_ecosystems": "Protected Mountain Biodiversity",
    "forest_area_change": "Change in Forest Area",
    "land_degraded": "Share of Degraded Land",
}

# Units shown in the map legend and hover text
UNITS = {
    "land_protected": "%",
    "land_degraded": "%",
    "mountain_ecosystems": "%",
    "annual_deforestation": "ha",
    "forest_area_change": "ha",
}

COLORSCALES = {
    "annual_deforestation": "YlOrRd",
    "land_degraded":        "YlOrRd",
    "land_protected":       "Greens",
    "mountain_ecosystems":  "Greens",
    "forest_area_change":   "RdYlGn",
}
DEFAULT_COLORSCALE = "Blues"

# Convert indicator key into a nice label
def nice_label(indicator_key: str) -> str:
    return DISPLAY_TITLES.get(indicator_key, indicator_key.replace("_", " ").title())

# Return the unit for a given indicator (or empty string if not defined)
def get_unit(indicator_key: str) -> str:
    return UNITS.get(indicator_key, "")

# Pick an ISO-3 identifier column from the GeoDataFrame
def _pick_id_col(gdf) -> str:
    if "ISO_A3_CLEAN" in gdf.columns:
        return "ISO_A3_CLEAN"
    if "ISO_A3" in gdf.columns:
        return "ISO_A3"
    if "Code" in gdf.columns:
        return "Code"
    raise ValueError("Missing ISO-3 country code column (expected ISO_A3_CLEAN, ISO_A3 or Code).")

# Build a choropleth map with two layers: missing values (grey) and real values
def build_map_figure(gdf, selected_indicator: str):
    # Basic checks so the app won't crash
    if gdf is None or len(gdf) == 0:
        raise ValueError("No data available for this selection (empty GeoDataFrame).")

    if selected_indicator not in gdf.columns:
        raise ValueError("No data available for this selection (indicator column missing).")

    if "geometry" not in gdf.columns:
        raise ValueError("Geometry missing in GeoDataFrame.")

    id_col = _pick_id_col(gdf)

    # Keep only the columns needed for the map
    name_col = next((c for c in ["Entity", "ADMIN", "NAME", "name"] if c in gdf.columns), None)
    if name_col is None:
        raise ValueError("No country name column found in GeoDataFrame.")

    map_df = gdf[[id_col, name_col, selected_indicator, "geometry"]].dropna(subset=[id_col]).copy()
    map_df = map_df.rename(columns={name_col: "Entity"})
    map_df[selected_indicator] = pd.to_numeric(map_df[selected_indicator], errors="coerce")

    # Build the legend title, including units when available
    unit = get_unit(selected_indicator)
    legend_title = f"{nice_label(selected_indicator)} ({unit})" if unit else nice_label(selected_indicator)

    # Hover value formatting
    def make_value_text(v):
        if pd.isna(v):
            return "No data"
        if unit == "ha":
            return f"{v:,.0f} {unit}"
        return f"{v:.1f} {unit}" if unit else f"{v:.1f}"

    map_df["value_text"] = map_df[selected_indicator].apply(make_value_text)

    # Convert geometries to GeoJSON so Plotly can draw country shapes
    geojson = json.loads(map_df.to_json())

    # Split into missing vs non-missing values
    missing_df = map_df[map_df[selected_indicator].isna()]
    value_df = map_df[map_df[selected_indicator].notna()]

    # Create an empty Plotly figure
    fig_map = go.Figure()

    # Layer 1: missing values (grey)
    if not missing_df.empty:
        fig_map.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=missing_df[id_col],
                featureidkey=f"properties.{id_col}",
                z=[0] * len(missing_df),
                colorscale=[[0, "lightgrey"], [1, "lightgrey"]],
                showscale=False,
                marker_line_color="black",
                marker_line_width=0.6,
                hovertext=missing_df["Entity"],
                customdata=missing_df[["value_text"]],
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    f"{nice_label(selected_indicator)}: %{{customdata[0]}}"
                    "<extra></extra>"
                ),
            )
        )

    # Layer 2: real values
    if not value_df.empty:
        fig_map.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=value_df[id_col],
                featureidkey=f"properties.{id_col}",
                z=value_df[selected_indicator],
                colorscale=COLORSCALES.get(selected_indicator, DEFAULT_COLORSCALE),
                colorbar=dict(
                    title=dict(text=legend_title, side="right"),
                    len=0.9,
                    thickness=18,
                    x=1.02,
                    xpad=12,
                ),
                marker_line_color="black",
                marker_line_width=0.6,
                hovertext=value_df["Entity"],
                customdata=value_df[["value_text"]],
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    f"{nice_label(selected_indicator)}: %{{customdata[0]}}"
                    "<extra></extra>"
                ),
            )
        )

    # Fit map nicely and remove background/axes
    fig_map.update_geos(
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        projection_type="natural earth",
        lataxis_range=[-60, 85],
        lonaxis_range=[-180, 180],
    )

    fig_map.update_layout(
        height=400,
        margin=dict(l=0, r=40, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="black",
    )

    caption = "Grey countries indicate missing data for the selected indicator and year."
    return fig_map, caption