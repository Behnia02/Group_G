import streamlit as st
from main import EnvironmentalData

from app.plots_map import build_map_figure, nice_label
from app.plots_charts import build_chart_figure

# Configure the Streamlit page
st.set_page_config(page_title="Project Okavango", layout="wide")

# Display a centered title using simple HTML
st.markdown(
    "<h1 style='text-align: center;'>Project Okavango</h1>",
    unsafe_allow_html=True
)

# Add a horizontal separator line
st.divider()

@st.cache_resource
def load_data() -> EnvironmentalData:
    # Create the data manager once and reuse it across Streamlit reruns
    return EnvironmentalData()

# Load the data manager so the rest of the app can query data quickly
data = load_data()

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------

with st.sidebar:
    # Sidebar section title and instruction text for the user
    st.header("Filters")
    st.caption("Select an indicator and a year to update the map and chart.")

    # List available indicators and let the user pick one.
    indicators = data.get_available_indicators()
    selected_indicator = st.selectbox(
        "Select Indicator",
        indicators,
        format_func=nice_label
    )

# ----------------------------
# YEAR SELECTION
# ----------------------------

# Get all available years for the chosen indicator
years = data.get_available_years(selected_indicator)

# If there are no years, stop
if not years:
    st.warning("No years available for this indicator.")
    st.stop()

# Default to the most recent year available
default_year = max(years)

# Let the user pick the year through a slider
selected_year = st.sidebar.select_slider(
    "Select Year",
    options=years,
    value=default_year,
)

# ----------------------------
# LOAD DATA FOR CURRENT SELECTION
# ----------------------------

# Load the GeoDataFrame for the selected indicator/year
with st.spinner("Loading data..."):
    gdf = data.get_geodata(selected_indicator, selected_year)

# ----------------------------
# MAP SECTION
# ----------------------------

# Section title for current selection
st.subheader(f"{nice_label(selected_indicator)} ({selected_year})")

try:
    # Build and display the choropleth map for the selected indicator
    fig_map, caption = build_map_figure(gdf, selected_indicator)
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except ValueError as e:
    # If the map can't be built, show a warning and stop
    st.warning(str(e))
    st.stop()

# Visual separator
st.divider()

# ----------------------------
# GRAPHS BELOW THE MAP
# ----------------------------

# Build the chart below the map (depending on the selected indicator)
fig_chart, title_or_msg = build_chart_figure(gdf, selected_indicator, selected_year)


if fig_chart is None:
    # If there is no chart to plot, show the returned message
    st.warning(title_or_msg)
else:
    # Otherwise, show the chart title and plot the figure
    st.subheader(title_or_msg)
    st.plotly_chart(fig_chart, use_container_width=True)

# Bottom divider
st.divider()