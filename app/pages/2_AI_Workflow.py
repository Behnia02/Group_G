import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AI Workflow",
    page_icon="🛰️",
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
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stNumberInput label {
        color: #888880 !important;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stNumberInput > div > div,
    [data-testid="stSidebar"] .stSlider > div > div {
        background-color: #f7f7f5;
        border: 0.5px solid #d0cdc6;
        color: #222220 !important;
        border-radius: 6px;
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
        font-size: 0.9rem;
        font-weight: 300;
        margin: 0;
    }

    .kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
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

    hr { border-color: #e0ddd6 !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #aaa !important; }
    [data-testid="stSpinner"] p { color: #555550; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background-color: #f7f7f5;
        border-bottom: 0.5px solid #e0ddd6;
    }
</style>
""", unsafe_allow_html=True)

# Session state defaults
if "ai_settings" not in st.session_state:
    st.session_state.ai_settings = {
        "latitude": -19.3,
        "longitude": 22.9,
        "zoom": 8,
        "image_width": 768,
        "image_height": 768,
    }

PRESET_LOCATIONS = {
    "Okavango Delta, Botswana": {"latitude": -19.3, "longitude": 22.9, "zoom": 8},
    "Lisbon, Portugal": {"latitude": 38.7223, "longitude": -9.1393, "zoom": 11},
    "Amazon Rainforest, Brazil": {"latitude": -3.1, "longitude": -60.0, "zoom": 7},
    "Borneo, Indonesia": {"latitude": 0.8, "longitude": 113.9, "zoom": 7},
    "Congo Basin": {"latitude": -0.5, "longitude": 15.2, "zoom": 6},
}

# Sidebar
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    st.page_link("streamlit_app.py", label="Back to Environmental Explorer", icon="🌍")
    st.divider()

    st.markdown("### 📍 Quick presets")
    preset_name = st.selectbox("Preset location", list(PRESET_LOCATIONS.keys()))

    if st.button("Load preset", use_container_width=True):
        preset = PRESET_LOCATIONS[preset_name]
        st.session_state.ai_settings["latitude"] = preset["latitude"]
        st.session_state.ai_settings["longitude"] = preset["longitude"]
        st.session_state.ai_settings["zoom"] = preset["zoom"]
        st.success("Preset loaded.")

    st.divider()

    st.markdown("### 🛰️ AI controls")
    with st.form("ai_controls"):
        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=float(st.session_state.ai_settings["latitude"]),
            step=0.0001,
            format="%.4f",
        )

        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=float(st.session_state.ai_settings["longitude"]),
            step=0.0001,
            format="%.4f",
        )

        zoom = st.slider(
            "Zoom",
            min_value=1,
            max_value=20,
            value=int(st.session_state.ai_settings["zoom"]),
        )

        image_width = st.select_slider(
            "Image width",
            options=[256, 512, 768, 1024],
            value=int(st.session_state.ai_settings["image_width"]),
        )

        image_height = st.select_slider(
            "Image height",
            options=[256, 512, 768, 1024],
            value=int(st.session_state.ai_settings["image_height"]),
        )

        save_settings = st.form_submit_button("Save settings", use_container_width=True)

if save_settings:
    st.session_state.ai_settings = {
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "image_width": image_width,
        "image_height": image_height,
    }
    st.success("AI workflow settings saved.")

settings = st.session_state.ai_settings

# Hero
st.markdown("""
<div class="okavango-hero">
    <h1>🛰️ AI Workflow</h1>
    <p>Select latitude, longitude, zoom, and image size for the area you want to analyse.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("streamlit_app.py", label="Back to Page 1 · Environmental Explorer", icon="🌍")
st.caption("This page is ready for the next step: fetching an image for these coordinates.")

# KPI row
st.markdown(f"""
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">Latitude</div>
        <div class="kpi-value">{settings["latitude"]:.4f}</div>
        <div class="kpi-sub">selected coordinate</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Longitude</div>
        <div class="kpi-value">{settings["longitude"]:.4f}</div>
        <div class="kpi-sub">selected coordinate</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Zoom</div>
        <div class="kpi-value">{settings["zoom"]}</div>
        <div class="kpi-sub">map/image zoom level</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Image size</div>
        <div class="kpi-value">{settings["image_width"]}×{settings["image_height"]}</div>
        <div class="kpi-sub">output dimensions</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Map preview
st.markdown('<div class="section-header">Selected Area Preview</div>', unsafe_allow_html=True)

preview_df = pd.DataFrame(
    {
        "lat": [settings["latitude"]],
        "lon": [settings["longitude"]],
    }
)

st.map(
    preview_df,
    zoom=int(settings["zoom"]),
    width="stretch",
    height=500,
)

st.divider()

# Debug / next-step helper
st.markdown('<div class="section-header">Current Parameters</div>', unsafe_allow_html=True)
st.code(
    f"latitude = {settings['latitude']}\n"
    f"longitude = {settings['longitude']}\n"
    f"zoom = {settings['zoom']}\n"
    f"image_width = {settings['image_width']}\n"
    f"image_height = {settings['image_height']}",
    language="python",
)

st.info(
    "Next step: use these saved parameters to download an image from the selected area "
    "and send that image to the AI model for description."
)