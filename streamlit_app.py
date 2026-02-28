import streamlit as st
from main import EnvironmentalData

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
    indicators
)

# ----------------------------
# YEAR SELECTION
# ----------------------------
years = data.get_available_years(selected_indicator)

if not years:
    st.warning("No years available for this indicator.")
    st.stop()

default_year = max(years)

selected_year = st.sidebar.selectbox(
    "Select Year",
    years,
    index=years.index(default_year)
)