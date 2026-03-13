# To run this Streamlit app from the project root use: python -m streamlit run streamlit_app.py
 
import streamlit as st
from main import EnvironmentalData
from app.plots_map import build_map_figure, nice_label
from app.plots_charts import build_chart_figure
 
# Page config
 
st.set_page_config(
    page_title="Project Okavango",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# Custom CSS
 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;1,400&family=Inter:wght@300;400;500&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
 
    .stApp { background-color: #f7f7f5; }
    [data-testid="stAppViewContainer"] > .main { background-color: #f7f7f5; }
    [data-testid="block-container"] { background-color: #f7f7f5; padding-top: 2rem; }
 
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 0.5px solid #e0ddd6;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown { color: #555550 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label {
        color: #888880 !important;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #f7f7f5;
        border: 0.5px solid #d0cdc6;
        color: #222220 !important;
        border-radius: 6px;
    }
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        color: #555550 !important;
        background-color: #f7f7f5;
        border: 0.5px solid #e0ddd6;
        border-radius: 6px;
    }
    [data-testid="stSidebar"] .streamlit-expanderContent {
        background-color: #f7f7f5;
        border: 0.5px solid #e0ddd6;
        border-top: none;
    }
 
    .okavango-hero {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        border-left: 3px solid #2d6a4f;
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
    .okavango-hero p { color: #888880; font-size: 0.9rem; font-weight: 300; margin: 0; }
 
    .kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card {
        flex: 1;
        background: #ffffff;
        border: 0.5px solid #e0ddd6;
        border-radius: 10px;
        padding: 1rem 1.2rem;
    }
    .kpi-label {
        font-size: 0.7rem; font-weight: 500; letter-spacing: 0.08em;
        text-transform: uppercase; color: #888880; margin-bottom: 0.3rem;
    }
    .kpi-value { font-family: 'Lora', serif; font-size: 1.5rem; color: #1a1a18; line-height: 1.1; }
    .kpi-sub { font-size: 0.75rem; color: #aaa; margin-top: 0.2rem; }
 
    .section-header {
        font-family: 'Lora', serif;
        font-size: 1.2rem; color: #1a1a18;
        border-bottom: 0.5px solid #e0ddd6;
        padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
 
    .stPlotlyChart {
        background-color: #ffffff;
        border-radius: 10px;
        border: 0.5px solid #e0ddd6;
        padding: 0.5rem;
    }
 
    hr { border-color: #e0ddd6 !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #aaa !important; }
    [data-testid="stSpinner"] p { color: #555550; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: #f7f7f5; border-bottom: 0.5px solid #e0ddd6; }
</style>
""", unsafe_allow_html=True)
 
# Data loading
 
@st.cache_resource(show_spinner="Initialising data pipeline…")
def load_data() -> EnvironmentalData:
    return EnvironmentalData()
 
data = load_data()
 
# Sidebar
 
# Add/edit descriptions to match your actual indicator names from get_available_indicators()
INDICATOR_DESCRIPTIONS = {
    "annual_deforestation":  "Total forest area lost per year (hectares). Does not account for reforestation.",
    "forest_area_change":    "Net annual change in forest area (hectares). Negative values mean net forest loss.",
    "land_degraded":         "Percentage of total land area classified as degraded due to human or natural causes.",
    "land_protected":        "Percentage of total land area under formal protection (national parks, reserves, etc.).",
    "mountain_ecosystems":   "Percentage of mountain area covered by protected biodiversity zones.",
}
 
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    if st.button("Go to AI Workflow"):
        st.switch_page("pages/2_AI_Workflow.py")
    st.divider()

    st.markdown("### 🌿 Filters")
    st.caption("Select an indicator and year to update the map and chart.")
    st.divider()

    indicators = data.get_available_indicators()
    selected_indicator = st.selectbox(
        "Indicator",
        indicators,
        format_func=nice_label,
    )

    years = data.get_available_years(selected_indicator)
    if not years:
        st.warning("No years available for this indicator.")
        st.stop()

    selected_year = st.select_slider(
        "Year",
        options=years,
        value=max(years),
    )

    st.divider()

    desc = INDICATOR_DESCRIPTIONS.get(
        selected_indicator,
        "No description available for this indicator."
    )
    with st.expander("About this indicator"):
        st.caption(desc)

# Load geodata
with st.spinner("Loading spatial data…"):
    gdf = data.get_geodata(selected_indicator, selected_year)

# Hero banner
st.markdown(f"""
<div class="okavango-hero">
    <h1>🌍 Project Okavango</h1>
    <p>Environmental data explorer · {nice_label(selected_indicator)} · {selected_year}</p>
</div>
""", unsafe_allow_html=True)

st.page_link(
    "pages/2_AI_Workflow.py",
    label="Open Page 2 · AI Workflow",
    icon="🛰️",
)
st.caption("Select latitude, longitude, and zoom for the image-based workflow.")

st.divider()

# KPI row
col_data = gdf[selected_indicator].dropna() if selected_indicator in gdf.columns else None

if col_data is not None and len(col_data) > 0:
    top_idx = col_data.idxmax()
    bot_idx = col_data.idxmin()
    name_col = next((c for c in ["ADMIN", "name", "NAME", "Entity"] if c in gdf.columns), None)
    top_name = gdf.loc[top_idx, name_col] if name_col else "N/A"
    bot_name = gdf.loc[bot_idx, name_col] if name_col else "N/A"

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-label">Countries with data</div>
            <div class="kpi-value">{int(col_data.notna().sum())}</div>
            <div class="kpi-sub">for {selected_year}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Global average</div>
            <div class="kpi-value">{col_data.mean():,.1f}</div>
            <div class="kpi-sub">median {col_data.median():,.1f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Highest</div>
            <div class="kpi-value">{top_name}</div>
            <div class="kpi-sub">{col_data.max():,.1f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Lowest</div>
            <div class="kpi-value">{bot_name}</div>
            <div class="kpi-sub">{col_data.min():,.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Map
st.markdown('<div class="section-header">World Map</div>', unsafe_allow_html=True)

try:
    fig_map, caption = build_map_figure(gdf, selected_indicator)
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except ValueError as e:
    st.warning(str(e))
    st.stop()

st.divider()

# Chart
fig_chart, title_or_msg = build_chart_figure(gdf, selected_indicator, selected_year)

if fig_chart is None:
    st.info(f"ℹ️ {title_or_msg}")
else:
    st.markdown(f'<div class="section-header">{title_or_msg}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_chart, use_container_width=True)

st.divider()