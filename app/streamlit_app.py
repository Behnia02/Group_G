import streamlit as st

from ai_workflow import render_ai_workflow
from plots_charts import build_chart_figure
from plots_map import build_map_figure, nice_label
from project_class import EnvironmentalData


st.set_page_config(
    page_title="Project Okavango",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

view_param = st.query_params.get("view", "explorer")
current_view = "AI Workflow" if view_param == "ai-workflow" else "Environmental Explorer"

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Inter:wght@300;400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp,
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="block-container"] {
            background-color: #f7f7f5;
        }

        [data-testid="block-container"] {
            padding-top: 2rem;
        }

        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 0.5px solid #e0ddd6;
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown {
            color: #555550 !important;
        }

        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stRadio label {
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

        .okavango-hero p {
            color: #888880;
            font-size: 1.05rem;
            font-weight: 300;
            margin: 0;
        }

        .kpi-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            flex: 1;
            background: #ffffff;
            border: 0.5px solid #e0ddd6;
            border-radius: 10px;
            padding: 1rem 1.2rem;
        }

        .kpi-label {
            font-size: 0.7rem;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #888880;
            margin-bottom: 0.3rem;
        }

        .kpi-value {
            font-family: 'Lora', serif;
            font-size: 1.5rem;
            color: #1a1a18;
            line-height: 1.1;
        }

        .kpi-sub {
            font-size: 0.75rem;
            color: #aaa;
            margin-top: 0.2rem;
        }

        .section-header {
            font-family: 'Lora', serif;
            font-size: 1.2rem;
            color: #1a1a18;
            border-bottom: 0.5px solid #e0ddd6;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }

        .stPlotlyChart {
            background-color: #ffffff;
            border-radius: 10px;
            border: 0.5px solid #e0ddd6;
            padding: 0.5rem;
        }

        .view-link-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            background: #ffffff;
            border: 0.5px solid #e0ddd6;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin: 0.25rem 0 1.25rem 0;
        }

        .view-link-copy {
            color: #66665f;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .view-link-btn {
            display: inline-block;
            text-decoration: none !important;
            background: #2d6a4f;
            color: white !important;
            padding: 0.7rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            white-space: nowrap;
        }

        .sidebar-nav-link {
            text-decoration: none !important;
            color: inherit !important;
            display: block;
            margin-bottom: 0.8rem;
        }

        .sidebar-nav-item {
            border-radius: 12px;
            border: 1px solid #e5e2db;
            background: #faf9f7;
            padding: 0.95rem 1rem;
            transition: all 0.18s ease;
        }

        .sidebar-nav-item.active {
            background: #eef6f1;
            border-color: #2d6a4f;
            box-shadow: inset 4px 0 0 #2d6a4f;
        }

        .sidebar-nav-label {
            display: block;
            color: #1f1f1c !important;
            font-size: 0.98rem;
            font-weight: 600;
            margin-bottom: 0.15rem;
        }

        .sidebar-nav-sub {
            display: block;
            color: #7a7872 !important;
            font-size: 0.82rem;
            line-height: 1.35;
        }

        hr { border-color: #e0ddd6 !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        header[data-testid="stHeader"] {
            background-color: #f7f7f5;
            border-bottom: 0.5px solid #e0ddd6;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Initialising data pipeline…")
def load_data() -> EnvironmentalData:
    return EnvironmentalData()


data = load_data()

with st.sidebar:
    st.markdown("### 🧭 Navigation")

    explorer_active = "active" if current_view == "Environmental Explorer" else ""
    ai_active = "active" if current_view == "AI Workflow" else ""

    st.markdown(
        f"""
        <a href="?view=explorer" target="_self" class="sidebar-nav-link">
            <div class="sidebar-nav-item {explorer_active}">
                <span class="sidebar-nav-label">🌍 Environmental Explorer</span>
                <span class="sidebar-nav-sub">Maps, indicators and trends</span>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <a href="?view=ai-workflow" target="_self" class="sidebar-nav-link">
            <div class="sidebar-nav-item {ai_active}">
                <span class="sidebar-nav-label">🛰️ AI Workflow</span>
                <span class="sidebar-nav-sub">Choose location and preview the area</span>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

if current_view == "AI Workflow":
    render_ai_workflow(data)
    st.stop()

INDICATOR_DESCRIPTIONS = {
    "annual_deforestation": "Total forest area lost per year (hectares). Does not account for reforestation.",
    "forest_area_change": "Net annual change in forest area (hectares). Negative values mean net forest loss.",
    "land_degraded": "Percentage of total land area classified as degraded due to human or natural causes.",
    "land_protected": "Percentage of total land area under formal protection (national parks, reserves, etc.).",
    "mountain_ecosystems": "Percentage of mountain area covered by protected biodiversity zones.",
}

with st.sidebar:
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
        "No description available for this indicator.",
    )
    with st.expander("About this indicator"):
        st.caption(desc)

with st.spinner("Loading spatial data…"):
    gdf = data.get_geodata(selected_indicator, selected_year)

st.markdown(
    f"""
    <div class="okavango-hero">
        <h1>🌍 Project Okavango</h1>
        <p>Environmental data explorer · {nice_label(selected_indicator)} · {selected_year}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="view-link-card">
        <div class="view-link-copy">
            Ready to analyse a specific place in more detail? Open the AI Workflow view to choose a location and preview it.
        </div>
        <a href="?view=ai-workflow" target="_self" class="view-link-btn">Open AI Workflow →</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

col_data = gdf[selected_indicator].dropna() if selected_indicator in gdf.columns else None

if col_data is not None and len(col_data) > 0:
    top_idx = col_data.idxmax()
    bot_idx = col_data.idxmin()
    name_col = next((c for c in ["ADMIN", "name", "NAME", "Entity"] if c in gdf.columns), None)

    top_name = gdf.loc[top_idx, name_col] if name_col else "N/A"
    bot_name = gdf.loc[bot_idx, name_col] if name_col else "N/A"

    st.markdown(
        f"""
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
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-header">World Map</div>', unsafe_allow_html=True)

try:
    fig_map, caption = build_map_figure(gdf, selected_indicator)
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

st.divider()

fig_chart, title_or_msg = build_chart_figure(gdf, selected_indicator, selected_year)

if fig_chart is None:
    st.info(f"ℹ️ {title_or_msg}")
else:
    st.markdown(f'<div class="section-header">{title_or_msg}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_chart, use_container_width=True)
