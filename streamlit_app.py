import streamlit as st
import matplotlib.pyplot as plt
from main import EnvironmentalData

st.set_page_config(page_title="Project Okavango", layout="wide")

st.title("Project Okavango")

def pretty_label(s):
    return s.replace("_", " ").title()

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

st.subheader(f"{pretty_label(selected_indicator)} — {selected_year}")

if gdf.empty:
    st.warning("No data available for this selection.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    gdf.plot(
        column=selected_indicator,
        ax=ax,
        legend=True,
        missing_kwds={"color": "lightgrey"},
    )

    ax.set_title(f"{pretty_label(selected_indicator)} ({selected_year})")
    ax.set_axis_off()

    st.pyplot(fig)

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