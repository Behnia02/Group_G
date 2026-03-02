import streamlit as st
from main import EnvironmentalData

from app.plots_map import build_map_figure, nice_label
from app.plots_charts import build_chart_figure

st.set_page_config(page_title="Project Okavango", layout="wide")

st.title("Project Okavango")

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
    format_func=nice_label
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

# ----------------------------
# MAP SECTION
# ----------------------------

st.subheader(f"{nice_label(selected_indicator)} ({selected_year})")

try:
    fig_map, caption = build_map_figure(gdf, selected_indicator)
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except ValueError as e:
    st.warning(str(e))
    st.stop()


# ----------------------------
# GRAPHS BELOW THE MAP
# ----------------------------

fig_chart, title_or_msg = build_chart_figure(gdf, selected_indicator, selected_year)

if fig_chart is None:
    st.warning(title_or_msg)
else:
    st.subheader(title_or_msg)
    st.plotly_chart(fig_chart, use_container_width=True)