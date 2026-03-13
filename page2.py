"""
page2.py
--------
Page 2 of the Project Okavango Streamlit app.

AI-powered satellite image analysis workflow:
  1. User selects latitude, longitude, and zoom level.
  2. A satellite image is downloaded from ESRI World Imagery.
  3. A vision model (llava) describes the image.
  4. A text model (llama3.2) assesses environmental risk.
  5. Results are displayed with a clear risk indicator.

Run from project root:
    python -m streamlit run page2.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.tile_utils import download_satellite_image
from app.ai_analysis import load_models_config, run_ai_pipeline

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Project Okavango · AI Analysis",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS  (matches Page 1 styling)
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;1,400&family=Inter:wght@300;400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f7f7f5; }
    [data-testid="stAppViewContainer"] > .main { background-color: #f7f7f5; }
    [data-testid="block-container"] { background-color: #f7f7f5; padding-top: 2rem; }
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 0.5px solid #e0ddd6;
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
    }
    .okavango-hero p { color: #888880; font-size: 0.9rem; font-weight: 300; margin: 0; }

    .risk-safe {
        background: #d4edda; border: 1px solid #28a745;
        border-radius: 10px; padding: 1.2rem 1.5rem;
        font-size: 1.1rem; color: #155724; font-weight: 500;
    }
    .risk-danger {
        background: #f8d7da; border: 1px solid #dc3545;
        border-radius: 10px; padding: 1.2rem 1.5rem;
        font-size: 1.1rem; color: #721c24; font-weight: 500;
    }
    .section-header {
        font-family: 'Lora', serif;
        font-size: 1.2rem; color: #1a1a18;
        border-bottom: 0.5px solid #e0ddd6;
        padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
    .description-box {
        background: #ffffff;
        border: 0.5px solid #e0ddd6;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        color: #444;
        font-size: 0.92rem;
        line-height: 1.6;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------

st.markdown("""
<div class="okavango-hero">
    <h1>🛰️ AI Satellite Analysis</h1>
    <p>Select a location · Download satellite imagery · Assess environmental risk with AI</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — location controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🛰️ Location Settings")
    st.caption("Choose coordinates and zoom to analyse a region.")
    st.divider()

    lat = st.number_input(
        "Latitude",
        min_value=-90.0,
        max_value=90.0,
        value=-3.0,
        step=0.5,
        help="Decimal degrees. Negative = South.",
    )
    lon = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=-60.0,
        step=0.5,
        help="Decimal degrees. Negative = West.",
    )
    zoom = st.slider(
        "Zoom level",
        min_value=5,
        max_value=17,
        value=12,
        help="Higher zoom = more detail. 17 ≈ 1 m/pixel.",
    )

    st.divider()

    # Quick preset locations
    st.caption("🔖 Quick presets")
    presets = {
        "Amazon Basin 🌳": (-3.0, -60.0, 12),
        "Sahara Desert 🏜️": (23.0, 12.0, 10),
        "Congo Rainforest 🌿": (-1.0, 24.0, 12),
        "Aral Sea (shrinking) 💧": (45.0, 60.0, 9),
        "Borneo deforestation 🪵": (1.0, 114.0, 11),
    }
    preset_choice = st.selectbox("Load a preset", ["— none —"] + list(presets.keys()))
    if preset_choice != "— none —":
        lat, lon, zoom = presets[preset_choice]
        st.info(f"📍 {preset_choice}\nLat {lat}, Lon {lon}, Zoom {zoom}")

    st.divider()
    run_button = st.button("🔍 Analyse this location", width=700, type="primary")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if not run_button:
    st.info(
        "👈 Set your coordinates in the sidebar and click **Analyse this location** to start."
    )
    st.stop()

# --- Step 1: Download satellite image ---

st.markdown('<div class="section-header">📡 Satellite Image</div>', unsafe_allow_html=True)

images_dir = Path("images")

with st.spinner(f"Downloading satellite image for ({lat}, {lon}) at zoom {zoom}…"):
    try:
        image_path = download_satellite_image(lat, lon, zoom, output_dir=images_dir)
    except Exception as e:
        st.error(f"Failed to download satellite image: {e}")
        st.stop()

col_img, col_desc = st.columns([1, 1], gap="large")

with col_img:
    st.image(str(image_path), caption=f"ESRI World Imagery · ({lat}, {lon}) · Zoom {zoom}", width=700)

# --- Step 2 & 3: Run AI pipeline ---

config = load_models_config("models.yaml")

with col_desc:
    st.markdown('<div class="section-header">🤖 Image Description</div>', unsafe_allow_html=True)

    with st.spinner("Running vision model — this may take 1–2 minutes…"):
        try:
            image_description, risk_assessment, at_risk = run_ai_pipeline(image_path, config)
        except Exception as e:
            st.error(
                f"AI pipeline failed: {e}\n\n"
                "Make sure Ollama is running (`ollama serve` in terminal) "
                "and the models are pulled."
            )
            st.stop()

    st.markdown(
        f'<div class="description-box">{image_description}</div>',
        unsafe_allow_html=True,
    )

# --- Step 4: Risk assessment ---

st.divider()
st.markdown('<div class="section-header">⚠️ Environmental Risk Assessment</div>', unsafe_allow_html=True)

if at_risk:
    st.markdown(
        "🔴 <span class='risk-danger'><b>ENVIRONMENTAL RISK DETECTED</b> — "
        "The AI flagged this area as potentially at risk.</span>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "🟢 <span class='risk-safe'><b>NO SIGNIFICANT RISK DETECTED</b> — "
        "The AI did not flag this area as being at environmental risk.</span>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("📋 Full AI assessment", expanded=True):
    st.markdown(
        f'<div class="description-box">{risk_assessment}</div>',
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    f"Model used for image description: `{config['vision_model']}` · "
    f"Model used for risk assessment: `{config['text_model']}`"
)
