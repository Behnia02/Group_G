import streamlit as st
from main import EnvironmentalData

st.write("App started successfully")

st.set_page_config(page_title="Project Okavango", layout="wide")

st.title("Project Okavango")

@st.cache_resource
def load_data() -> EnvironmentalData:
    """
    Create the data manager once and reuse it across Streamlit reruns.
    """
    return EnvironmentalData()

data = load_data()

st.success("Data loaded successfully!")

indicators = data.get_available_indicators()
st.write("Available Indicators:")
st.write(indicators)