# To run this Streamlit app from the project root use: python -m streamlit run app/streamlit_app.py

import streamlit as st
from main import EnvironmentalData    
from app.plots_map import build_map_figure, nice_label
from app.plots_charts import build_chart_figure

# Streamlit page setup
st.set_page_config(page_title="Project Okavango", layout="wide")

# Title
st.markdown(
    "<h1 style='text-align: center;'>Project Okavango</h1>",
    unsafe_allow_html=True
)

st.divider()

@st.cache_resource
def load_data() -> EnvironmentalData:
    # Keep one data manager instance across reruns so the app stays fast
    return EnvironmentalData()

# Load once, then reuse on widget interactions
data = load_data()

# SIDEBAR FILTERS

with st.sidebar:
    st.header("Filters")
    st.caption("Select an indicator and a year to update the map and chart.")

    # List available indicators and let the user pick one.
    indicators = data.get_available_indicators()
    selected_indicator = st.selectbox(
        "Select Indicator",
        indicators,
        format_func=nice_label
    )

# Year options depend on the selected indicator

years = data.get_available_years(selected_indicator)

# If there are no years, stop
if not years:
    st.warning("No years available for this indicator.")
    st.stop()

# Start on the latest available year
default_year = max(years)

selected_year = st.sidebar.select_slider(
    "Select Year",
    options=years,
    value=default_year,
)

# Pull the GeoDataFrame for the current selection
with st.spinner("Loading data..."):
    gdf = data.get_geodata(selected_indicator, selected_year)

# MAP SECTION

st.subheader(f"{nice_label(selected_indicator)} ({selected_year})")

try:
    fig_map, caption = build_map_figure(gdf, selected_indicator)
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except ValueError as e:
    # If the map can't be built, show a warning and stop
    st.warning(str(e))
    st.stop()

st.divider()

# Chart section (type depends on the indicator)
fig_chart, title_or_msg = build_chart_figure(gdf, selected_indicator, selected_year)

if fig_chart is None:
    # Some indicators may not have a chart view
    st.warning(title_or_msg)
else:
    st.subheader(title_or_msg)
    st.plotly_chart(fig_chart, use_container_width=True)

st.divider()