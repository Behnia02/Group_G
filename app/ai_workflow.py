import unicodedata

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
from tile_utils import download_satellite_image

try:
    from country_state_city import City, Country, State
except ImportError:
    City = Country = State = None


def render_ai_workflow():
    st.markdown("""
    <style>
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
            font-size: 0.95rem;
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
            margin-bottom: 0.5rem;
        }

        .kpi-value {
            font-family: 'Lora', serif;
            font-size: 1.5rem;
            color: #1a1a18;
            line-height: 1.1;
            word-break: break-word;
        }

        .section-header {
            font-family: 'Lora', serif;
            font-size: 1.2rem;
            color: #1a1a18;
            border-bottom: 0.5px solid #e0ddd6;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
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

        .satellite-card {
            background: #ffffff;
            border: 0.5px solid #e0ddd6;
            border-radius: 12px;
            padding: 1.2rem;
            margin-top: 1.25rem;
        }

        .satellite-copy {
            color: #66665f;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 0.9rem;
        }

        div[data-testid="stNumberInput"] input {
            background-color: #fcfcfa !important;
            border: 1px solid #d8d5ce !important;
            border-radius: 10px !important;
            color: #1a1a18 !important;
        }

        div[data-testid="stNumberInput"] label {
            color: #888880 !important;
            font-size: 0.72rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }
    </style>
    """, unsafe_allow_html=True)

    def ascii_text(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", str(text))
        text = text.encode("ascii", "ignore").decode("ascii")
        text = " ".join(text.split())
        return text.strip()

    def safe_text(text: str, fallback: str = "Unknown") -> str:
        cleaned = ascii_text(text)
        return cleaned if cleaned else fallback

    @st.cache_data(show_spinner=False)
    def get_country_names() -> list[str]:
        if Country is None:
            return ["Portugal"]
        try:
            countries = Country.get_countries()
            names = sorted(
                [safe_text(c.name, fallback="") for c in countries if safe_text(c.name, fallback="")]
            )
            return names if names else ["Portugal"]
        except Exception:
            return ["Portugal"]

    @st.cache_data(show_spinner=False)
    def get_country_code(country_name: str):
        if Country is None:
            return None
        try:
            for country in Country.get_countries():
                if safe_text(country.name, fallback="") == country_name:
                    return country.iso2
        except Exception:
            return None
        return None

    @st.cache_data(show_spinner=False)
    def get_region_names(country_name: str) -> list[str]:
        if State is None:
            return []
        country_code = get_country_code(country_name)
        if not country_code:
            return []
        try:
            states = State.get_states_of_country(country_code)
            return sorted(
                [safe_text(s.name, fallback="") for s in states if safe_text(s.name, fallback="")]
            )
        except Exception:
            return []

    @st.cache_data(show_spinner=False)
    def get_region_code(country_name: str, region_name: str):
        if State is None:
            return None
        country_code = get_country_code(country_name)
        if not country_code:
            return None
        try:
            for state in State.get_states_of_country(country_code):
                if safe_text(state.name, fallback="") == region_name:
                    return state.iso_code
        except Exception:
            return None
        return None

    @st.cache_data(show_spinner=False)
    def get_city_names(country_name: str, region_name: str = "") -> list[str]:
        if City is None:
            return []
        country_code = get_country_code(country_name)
        if not country_code:
            return []

        def normalize_city_names(cities) -> list[str]:
            names = []
            seen = set()
            for city in cities:
                name = safe_text(city.name, fallback="")
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
            return sorted(names)

        if region_name:
            region_code = get_region_code(country_name, region_name)
            if not region_code:
                return []
            try:
                cities = City.get_cities_of_state(country_code, region_code)
                return normalize_city_names(cities)
            except Exception:
                return []

        try:
            if hasattr(City, "get_cities_of_country"):
                cities = City.get_cities_of_country(country_code)
                return normalize_city_names(cities)
        except Exception:
            pass

        if State is None:
            return []

        try:
            all_cities = []
            for state in State.get_states_of_country(country_code):
                region_code = getattr(state, "iso_code", None)
                if not region_code:
                    continue
                try:
                    all_cities.extend(City.get_cities_of_state(country_code, region_code))
                except Exception:
                    continue
            return normalize_city_names(all_cities)
        except Exception:
            return []

    @st.cache_data(show_spinner=False)
    def geocode_place(country: str, region: str, city: str) -> tuple[float | None, float | None]:
        query_parts = [city.strip(), region.strip(), country.strip()]
        query = ", ".join(part for part in query_parts if part)
        if not query:
            return None, None

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "accept-language": "en",
        }
        headers = {
            "User-Agent": "ProjectOkavango/1.0 (student project)",
            "Accept-Language": "en",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            if not results:
                return None, None
            return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception:
            return None, None

    @st.cache_data(show_spinner=False)
    def reverse_geocode(lat: float, lon: float) -> tuple[str, str]:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 10,
            "accept-language": "en",
        }
        headers = {
            "User-Agent": "ProjectOkavango/1.0 (student project)",
            "Accept-Language": "en",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            address = data.get("address", {})
            country = safe_text(address.get("country", ""))
            city = safe_text(
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or address.get("county")
                or ""
            )
            return country, city
        except Exception:
            return "Unknown", "Unknown"

    country_options = get_country_names()

    if "ai_settings" not in st.session_state:
        st.session_state.ai_settings = {
            "latitude": 38.7223,
            "longitude": -9.1393,
            "zoom": 11,
            "country": "Portugal" if "Portugal" in country_options else country_options[0],
            "region": "",
            "city": "Lisbon",
        }

    if "sync_from_settings" not in st.session_state:
        st.session_state.sync_from_settings = True

    if "location_mode" not in st.session_state:
        st.session_state.location_mode = "By coordinates"

    if "satellite_image_path" not in st.session_state:
        st.session_state.satellite_image_path = None

    if (
        "lat_input" not in st.session_state
        or "lon_input" not in st.session_state
        or "zoom_input" not in st.session_state
        or "place_country" not in st.session_state
        or "place_region" not in st.session_state
        or "place_city" not in st.session_state
        or st.session_state.sync_from_settings
    ):
        settings = st.session_state.ai_settings
        st.session_state.lat_input = f"{settings['latitude']:.4f}"
        st.session_state.lon_input = f"{settings['longitude']:.4f}"
        st.session_state.zoom_input = int(settings["zoom"])

        default_country = settings["country"]
        if default_country not in country_options:
            default_country = "Portugal" if "Portugal" in country_options else country_options[0]
        st.session_state.place_country = default_country

        region_options_init = get_region_names(default_country)
        default_region = settings.get("region", "")
        if default_region not in region_options_init:
            default_region = region_options_init[0] if region_options_init else ""
        st.session_state.place_region = default_region

        city_options_init = get_city_names(default_country, default_region)
        default_city = settings.get("city", "")
        if default_city not in city_options_init:
            default_city = city_options_init[0] if city_options_init else ""
        st.session_state.place_city = default_city

        st.session_state.sync_from_settings = False

    with st.sidebar:
        st.markdown("### 🛰️ AI controls")
        st.markdown("##### Location method")

        is_coordinates = st.session_state.location_mode == "By coordinates"
        is_country_city = st.session_state.location_mode == "By country and city"

        st.markdown(
            f"""
            <style>
            div[data-testid="stButton"][data-key="mode_coordinates"] button,
            div.st-key-mode_coordinates button {{
                width: 100% !important;
                border-radius: 12px !important;
                min-height: 3rem !important;
                border: {"2px solid #000000" if is_coordinates else "1px solid #d8d5ce"} !important;
                background: #ffffff !important;
                color: #1a1a18 !important;
                font-size: 0.86rem !important;
                font-weight: 600 !important;
                letter-spacing: 0.04em !important;
                box-shadow: none !important;
                outline: none !important;
                margin-bottom: 0.4rem !important;
            }}

            div[data-testid="stButton"][data-key="mode_coordinates"] button:hover,
            div[data-testid="stButton"][data-key="mode_coordinates"] button:focus,
            div[data-testid="stButton"][data-key="mode_coordinates"] button:focus-visible,
            div.st-key-mode_coordinates button:hover,
            div.st-key-mode_coordinates button:focus,
            div.st-key-mode_coordinates button:focus-visible {{
                border: 2px solid #000000 !important;
                background: #ffffff !important;
                color: #1a1a18 !important;
                box-shadow: none !important;
                outline: none !important;
            }}

            div[data-testid="stButton"][data-key="mode_country_city"] button,
            div.st-key-mode_country_city button {{
                width: 100% !important;
                border-radius: 12px !important;
                min-height: 3rem !important;
                border: {"2px solid #000000" if is_country_city else "1px solid #d8d5ce"} !important;
                background: #ffffff !important;
                color: #1a1a18 !important;
                font-size: 0.86rem !important;
                font-weight: 600 !important;
                letter-spacing: 0.04em !important;
                box-shadow: none !important;
                outline: none !important;
                margin-bottom: 0.4rem !important;
            }}

            div[data-testid="stButton"][data-key="mode_country_city"] button:hover,
            div[data-testid="stButton"][data-key="mode_country_city"] button:focus,
            div[data-testid="stButton"][data-key="mode_country_city"] button:focus-visible,
            div.st-key-mode_country_city button:hover,
            div.st-key-mode_country_city button:focus,
            div.st-key-mode_country_city button:focus-visible {{
                border: 2px solid #000000 !important;
                background: #ffffff !important;
                color: #1a1a18 !important;
                box-shadow: none !important;
                outline: none !important;
            }}
            </style>
            <div class="mode-switch"></div>
            """,
            unsafe_allow_html=True,
        )

        mode_container = st.container()

        with mode_container:
            if st.button(
                "📍 Coordinates",
                key="mode_coordinates",
                use_container_width=True,
            ):
                st.session_state.location_mode = "By coordinates"
                st.rerun()

            if st.button(
                "🌍 Country · Region · City",
                key="mode_country_city",
                use_container_width=True,
            ):
                st.session_state.location_mode = "By country and city"
                st.rerun()

        st.slider("Zoom", min_value=1, max_value=20, key="zoom_input")

        if st.session_state.location_mode == "By coordinates":
            try:
                lat_default = float(str(st.session_state.lat_input).replace(",", "."))
            except Exception:
                lat_default = float(st.session_state.ai_settings["latitude"])

            try:
                lon_default = float(str(st.session_state.lon_input).replace(",", "."))
            except Exception:
                lon_default = float(st.session_state.ai_settings["longitude"])

            latitude_value = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=lat_default,
                step=0.0001,
                format="%.4f",
                help="Value between -90 and 90",
            )

            longitude_value = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=lon_default,
                step=0.0001,
                format="%.4f",
                help="Value between -180 and 180",
            )

            st.session_state.lat_input = f"{latitude_value:.4f}"
            st.session_state.lon_input = f"{longitude_value:.4f}"

            st.caption("Enter exact coordinates to preview a specific location.")

            if st.button("Save coordinates", use_container_width=True):
                country, city = reverse_geocode(latitude_value, longitude_value)
                st.session_state.ai_settings = {
                    "latitude": latitude_value,
                    "longitude": longitude_value,
                    "zoom": int(st.session_state.zoom_input),
                    "country": country,
                    "region": st.session_state.ai_settings.get("region", ""),
                    "city": city,
                }
                st.session_state.satellite_image_path = None
                st.session_state.sync_from_settings = True
                st.rerun()

        else:
            selected_country = st.selectbox("Country", options=country_options, key="place_country")

            region_options = get_region_names(selected_country)
            if region_options:
                region_choices = [""] + region_options
                if st.session_state.place_region not in region_choices:
                    st.session_state.place_region = ""
                selected_region = st.selectbox(
                    "Region",
                    options=region_choices,
                    key="place_region",
                    format_func=lambda region: region if region else "All regions (optional)",
                )
            else:
                selected_region = ""
                st.session_state.place_region = ""
                st.selectbox("Region", options=["No region filter needed"], disabled=True)

            city_options = get_city_names(selected_country, selected_region)
            if city_options:
                if st.session_state.place_city not in city_options:
                    st.session_state.place_city = city_options[0]
                selected_city = st.selectbox("City", options=city_options, key="place_city")
            else:
                selected_city = ""
                st.selectbox("City", options=["No cities found"], disabled=True)

            st.caption("Choose a country, optionally filter by region, and then choose a city.")

            preview_lat, preview_lon = (None, None)
            if selected_country and selected_city:
                preview_lat, preview_lon = geocode_place(selected_country, selected_region, selected_city)

            if st.button("Use selected place", use_container_width=True):
                if preview_lat is None or preview_lon is None:
                    st.error("Could not find coordinates for the selected location.")
                else:
                    st.session_state.ai_settings = {
                        "latitude": preview_lat,
                        "longitude": preview_lon,
                        "zoom": int(st.session_state.zoom_input),
                        "country": selected_country,
                        "region": selected_region,
                        "city": selected_city,
                    }
                    st.session_state.satellite_image_path = None
                    st.session_state.sync_from_settings = True
                    st.rerun()

    settings = st.session_state.ai_settings

    st.markdown("""
    <div class="okavango-hero">
        <h1>🛰️ AI Workflow</h1>
        <p>Select the area using coordinates or by choosing country, region and city.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="view-link-card">
        <div class="view-link-copy">
            Want to go back to the global indicators view? Open the Environmental Explorer.
        </div>
        <a href="?view=explorer" target="_self" class="view-link-btn">Open Environmental Explorer →</a>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-label">Latitude</div>
            <div class="kpi-value">{settings["latitude"]:.4f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Longitude</div>
            <div class="kpi-value">{settings["longitude"]:.4f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Country</div>
            <div class="kpi-value">{settings["country"]}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">City</div>
            <div class="kpi-value">{settings["city"]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Selected Area Preview</div>', unsafe_allow_html=True)

    preview_df = pd.DataFrame({"lat": [settings["latitude"]], "lon": [settings["longitude"]]})

    view_state = pdk.ViewState(
        latitude=settings["latitude"],
        longitude=settings["longitude"],
        zoom=settings["zoom"],
        pitch=0,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=preview_df,
        get_position="[lon, lat]",
        get_radius=120,
        get_fill_color=[214, 76, 76, 180],
        pickable=True,
    )

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": f'{settings["city"]}, {settings["country"]}'},
    )

    st.pydeck_chart(deck, use_container_width=True)

    st.markdown('<div class="section-header">Satellite Image</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="satellite-card">
            <div class="satellite-copy">
                Generate a stitched ESRI World Imagery snapshot for the currently selected area.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Generate satellite image", use_container_width=True):
        try:
            with st.spinner("Generating satellite image..."):
                image_path = download_satellite_image(
                    lat=float(settings["latitude"]),
                    lon=float(settings["longitude"]),
                    zoom=int(settings["zoom"]),
                    output_dir="images",
                )
            st.session_state.satellite_image_path = str(image_path)
        except Exception as exc:
            st.session_state.satellite_image_path = None
            st.error(f"Could not generate the satellite image: {exc}")

    if st.session_state.satellite_image_path:
        st.image(
            st.session_state.satellite_image_path,
            caption=(
                f'{settings["city"]}, {settings["country"]} '
                f'({settings["latitude"]:.4f}, {settings["longitude"]:.4f})'
            ),
            use_container_width=True,
        )
        st.caption(f"Saved to `{st.session_state.satellite_image_path}`")
