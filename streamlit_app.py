import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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
# GRAPHS BELOW THE MAP
# ----------------------------

# We build graphs from the same data used in the map (gdf)
df_all = gdf.copy()

# Make sure the chosen indicator exists and is numeric
if selected_indicator not in df_all.columns:
    st.warning("No data available for the graph.")
    st.stop()

df_all[selected_indicator] = pd.to_numeric(df_all[selected_indicator], errors="coerce")

# ----------------------------
# 1) % LAND PROTECTED AND MOUNTAIN ECOSYSTEMS -> DISTRIBUTION (HISTOGRAM BY 10% BINS)
# ----------------------------
if selected_indicator in ["land_protected", "mountain_ecosystems"]:
    st.subheader(f"Distribution of Countries by Range: {pretty_label(selected_indicator)} ({selected_year})")

    # Keep only valid % values (0..100)
    vals = df_all[selected_indicator].dropna().clip(0, 100)

    if vals.empty:
        st.warning("No data available for histogram.")
    else:
        # Create bins: 0–10, 10–20, ..., 90–100
        bins = list(range(0, 110, 10))
        cats = pd.cut(vals, bins=bins, include_lowest=True, right=False)

        # Count how many countries fall into each range
        counts = cats.value_counts().sort_index()

        # Convert counts to % of countries (normalized histogram)
        pct = (counts / counts.sum() * 100).round(1)

        # Prepare the dataframe for Plotly
        hist_df = pd.DataFrame({
            "Range": counts.index.astype(str),
            "% of countries": pct.values,
            "Countries (count)": counts.values,
        })

        # Color bars like the map: scale colors relative to the max in the selected year (so the highest “active” range becomes the brightest color)
        bin_mid = pd.Series([5, 15, 25, 35, 45, 55, 65, 75, 85, 95])
        max_val = max(float(vals.max()), 1e-9)
        hist_df["bin_scaled"] = (bin_mid / max_val).clip(0, 1)

        # Bar chart
        fig = px.bar(
            hist_df,
            x="Range",
            y="% of countries",
            color="bin_scaled",
            color_continuous_scale="Viridis",
            custom_data=["Range", "% of countries", "Countries (count)"],
        )

        # No legend needed
        fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))

        # Axis labels
        fig.update_xaxes(title=f"Ranges of {pretty_label(selected_indicator)} (%)")
        fig.update_yaxes(title="% of countries")

        # Hover: show range + % + count
        fig.update_traces(
            hovertemplate=(
                "<b>% of countries:</b> %{customdata[1]:.1f}%<br>"
                "Countries (count): %{customdata[2]}<br>"
                "Range: %{customdata[0]}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# 2) DEFORESTATION -> DISTRIBUTION (BINS BY MAGNITUDE)
# ----------------------------
elif selected_indicator == "annual_deforestation":
    st.subheader(f"Distribution of Countries by Range: {pretty_label(selected_indicator)} ({selected_year})")

    # Deforestation values are very skewed, so we use magnitude bins
    vals = df_all[selected_indicator].dropna().clip(lower=0)

    if vals.empty:
        st.warning("No data available for histogram.")
    else:
        # Magnitude bins (ha): 0–1k, 1k–10k, ..., >1M
        bins = [-0.1, 1_000, 10_000, 100_000, 1_000_000, float("inf")]
        labels = ["0–1k", "1k–10k", "10k–100k", "100k–1M", ">1M"]

        cats = pd.cut(vals, bins=bins, labels=labels)
        counts = cats.value_counts().reindex(labels, fill_value=0)
        pct = (counts / counts.sum() * 100).round(1)

        hist_df = pd.DataFrame({
            "Range": labels,
            "% of countries": pct.values,
            "Countries (count)": counts.values,
        })

        # Color bars low -> high with Viridis
        hist_df["bin_level"] = list(range(1, len(labels) + 1))

        fig = px.bar(
            hist_df,
            x="Range",
            y="% of countries",
            color="bin_level",
            color_continuous_scale="Viridis",
            custom_data=["Range", "% of countries", "Countries (count)"],
        )

        fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_xaxes(title=f"Ranges of {pretty_label(selected_indicator)} (ha)")
        fig.update_yaxes(title="% of countries")

        fig.update_traces(
            hovertemplate=(
                "<b>% of countries:</b> %{customdata[1]:.1f}%<br>"
                "Countries (count): %{customdata[2]}<br>"
                "Range: %{customdata[0]}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# 3) FOREST AREA CHANGE -> TOP GAINS VS TOP LOSSES
# ----------------------------
elif selected_indicator == "forest_area_change":
    st.subheader(f"Top 5 & Bottom 5 Countries: {pretty_label(selected_indicator)} ({selected_year})")

    # Remove missing values
    tmp = df_all.dropna(subset=[selected_indicator])

    # Pick the largest positive changes (top 5) and most negative (bottom 5)
    gains = tmp[tmp[selected_indicator] > 0].nlargest(5, selected_indicator)
    losses = tmp[tmp[selected_indicator] < 0].nsmallest(5, selected_indicator)

    plot_df = pd.concat([gains, losses], ignore_index=True)

    if plot_df.empty:
        st.warning("No positive/negative values available for this year.")
    else:
        # Label each bar as Top 5 or Bottom 5
        plot_df["Group"] = plot_df[selected_indicator].apply(lambda x: "Top 5" if x > 0 else "Bottom 5")

        # Pre-format values for the hover
        unit = UNITS.get(selected_indicator, "")
        plot_df["value_text"] = plot_df[selected_indicator].apply(lambda v: f"{v:,.0f} {unit}".rstrip())

        # Sort so gains appear above losses
        plot_df = plot_df.sort_values(selected_indicator, ascending=False)

        fig = px.bar(
            plot_df,
            x=selected_indicator,
            y="Entity",
            orientation="h",
            color=selected_indicator,              # map-like coloring
            color_continuous_scale="Viridis",
            category_orders={"Entity": plot_df["Entity"].tolist()},
            custom_data=["Group", "value_text"],
        )

        # Hide color legend (not needed)
        fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))

        # Axis labels
        fig.update_xaxes(title="Change in Forest Area (ha)", zeroline=True, tickformat=".2s")
        fig.update_yaxes(title="")

        # Hover: country + group + value
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b> (%{customdata[0]})<br>"
                "Change in Forest Area: %{customdata[1]}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# 4) DEFAULT -> TOP 5 + BOTTOM 5 (USED FOR DEGRADED LAND)
# ----------------------------
else:
    st.subheader(f"Top 5 & Bottom 5 Countries: {pretty_label(selected_indicator)} ({selected_year})")

    # Remove missing values
    tmp = df_all.dropna(subset=[selected_indicator])

    if tmp.empty:
        st.warning("No ranking data available.")
    else:
        # Top 5 and Bottom 5 by the indicator value
        top = tmp.nlargest(5, selected_indicator)
        bottom = tmp.nsmallest(5, selected_indicator)

        # Avoid overlap (same country in top and bottom)
        key = "Code" if "Code" in tmp.columns else "Entity"
        bottom = bottom[~bottom[key].isin(top[key])]

        # Combine and sort for display
        plot_df = (
            pd.concat([top, bottom], ignore_index=True)
            .drop_duplicates(subset=[key], keep="first")
            .sort_values(selected_indicator, ascending=False)
        )

        # Mark each row as Top 5 or Bottom 5
        top_keys = set(top[key].tolist())
        plot_df["Group"] = plot_df[key].apply(lambda v: "Top 5" if v in top_keys else "Bottom 5")

        # Pre-format values for hover (add % if available)
        unit = UNITS.get(selected_indicator, "")
        plot_df["value_text"] = plot_df[selected_indicator].apply(lambda v: f"{v:.1f}{unit}" if unit else f"{v:.1f}")

        # X axis label
        x_label = f"{pretty_label(selected_indicator)} ({unit})" if unit else pretty_label(selected_indicator)

        fig = px.bar(
            plot_df,
            x=selected_indicator,
            y="Entity",
            orientation="h",
            color=selected_indicator,             
            color_continuous_scale="Viridis",
            category_orders={"Entity": plot_df["Entity"].tolist()},
            custom_data=["Group", "value_text"],
        )

        fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_xaxes(title=x_label, tickformat=".2s")
        fig.update_yaxes(title="")

        # Hover: country + group + value
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b> (%{customdata[0]})<br>"
                f"{pretty_label(selected_indicator)}: %{{customdata[1]}}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)
