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


# ----------------------------
# GRAPHS BELOW THE MAP
# ----------------------------
