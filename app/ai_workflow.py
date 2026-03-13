import unicodedata

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
from country_state_city import City, Country, State


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
            font-size: 0.9rem;
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
    def get_country_list() -> list:
        try:
            countries = Country.get_countries()
            return sorted(countries, key=lambda x: x.name)
        except Exception:
            return []

    @st.cache_data(show_spinner=False)
    def get_country_names() -> list[str]:
        return [safe_text(c.name, fallback="") for c in get_country_list() if safe_text(c.name, fallback="")]

    @st.cache_data(show_spinner=False)
    def get_country_code(country_name: str):
        for country in get_country_list():
            if safe_text(country.name, fallback="") == country_name:
                return country.iso2
        return None

    @st.cache_data(show_spinner=False)
    def get_regions_for_country(country_name: str) -> list:
        country_code = get_country_code(country_name)
        if not country_code:
            return []

        try:
            states = State.get_states_of_country(country_code)
            return sorted(states, key=lambda x: x.name)
        except Exception:
            return []

    @st.cache_data(show_spinner=False)
    def get_region_names(country_name: str) -> list[str]:
        return [
            safe_text(s.name, fallback="")
            for s in get_regions_for_country(country_name)
            if safe_text(s.name, fallback="")
        ]

    @st.cache_data(show_spinner=False)
    def get_region_code(country_name: str, region_name: str):
        for state in get_regions_for_country(country_name):
            if safe_text(state.name, fallback="") == region_name:
                return state.iso_code
        return None

    @st.cache_data(show_spinner=False)
    def get_cities_for_country_region(country_name: str, region_name: str) -> list:
        country_code = get_country_code(country_name)
        region_code = get_region_code(country_name, region_name)

        if not country_code or not region_code:
            return []

        try:
            cities = City.get_cities_of_state(country_code, region_code)
            return sorted(cities, key=lambda x: x.name)
        except Exception:
            return []

    @st.cache_data(show_spinner=False)
    def get_city_names(country_name: str, region_name: str) -> list[str]:
        names = []
        seen = set()

        for city in get_cities_for_country_region(country_name, region_name):
            city_name = safe_text(city.name, fallback="")
            if city_name and city_name not in seen:
                seen.add(city_name)
                names.append(city_name)

        return names

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
    if not country_options:
        country_options = ["Portugal"]

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

        city_options_init = get_city_names(default_country, default_region) if default_region else []
        default_city = settings["city"]
        if default_city not in city_options_init:
            default_city = city_options_init[0] if city_options_init else ""

        st.session_state.place_city = default_city
        st.session_state.sync_from_settings = False

    with st.sidebar:
        st.markdown("### 🛰️ AI controls")

        st.radio(
            "Location method",
            ["By coordinates", "By country and city"],
            key="location_mode",
        )

        st.slider("Zoom", min_value=1, max_value=20, key="zoom_input")

        if st.session_state.location_mode == "By coordinates":
            st.text_input("Latitude", key="lat_input")
            st.text_input("Longitude", key="lon_input")

            st.text_input("Country", value=st.session_state.ai_settings["country"], disabled=True)
            st.text_input("City", value=st.session_state.ai_settings["city"], disabled=True)

            if st.button("Save coordinates", use_container_width=True):
                try:
                    latitude = float(st.session_state.lat_input.replace(",", "."))
                    longitude = float(st.session_state.lon_input.replace(",", "."))

                    if not (-90 <= latitude <= 90):
                        st.error("Latitude must be between -90 and 90.")
                    elif not (-180 <= longitude <= 180):
                        st.error("Longitude must be between -180 and 180.")
                    else:
                        country, city = reverse_geocode(latitude, longitude)
                        st.session_state.ai_settings = {
                            "latitude": latitude,
                            "longitude": longitude,
                            "zoom": int(st.session_state.zoom_input),
                            "country": country,
                            "region": st.session_state.ai_settings.get("region", ""),
                            "city": city,
                        }
                        st.session_state.sync_from_settings = True
                        st.rerun()
                except ValueError:
                    st.error("Latitude and longitude must be valid numbers.")

        else:
            selected_country = st.selectbox(
                "Country",
                options=country_options,
                key="place_country",
            )

            region_options = get_region_names(selected_country)
            if region_options:
                if st.session_state.place_region not in region_options:
                    st.session_state.place_region = region_options[0]

                selected_region = st.selectbox(
                    "Region",
                    options=region_options,
                    key="place_region",
                )
            else:
                selected_region = ""
                st.selectbox("Region", options=["No regions found"], disabled=True)

            city_options = get_city_names(selected_country, selected_region) if selected_region else []
            if city_options:
                if st.session_state.place_city not in city_options:
                    st.session_state.place_city = city_options[0]

                selected_city = st.selectbox(
                    "City",
                    options=city_options,
                    key="place_city",
                )
            else:
                selected_city = ""
                st.selectbox("City", options=["No cities found"], disabled=True)

            preview_lat, preview_lon = (None, None)
            if selected_country and selected_region and selected_city:
                preview_lat, preview_lon = geocode_place(selected_country, selected_region, selected_city)

            st.text_input(
                "Latitude",
                value="" if preview_lat is None else f"{preview_lat:.4f}",
                disabled=True,
            )
            st.text_input(
                "Longitude",
                value="" if preview_lon is None else f"{preview_lon:.4f}",
                disabled=True,
            )

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
                    st.session_state.sync_from_settings = True
                    st.rerun()

    settings = st.session_state.ai_settings

    st.markdown("""
    <div class="okavango-hero">
        <h1>🛰️ AI Workflow</h1>
        <p>Select the area using coordinates or by choosing country, region and city.</p>
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