import unicodedata

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


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
    def get_country_list() -> list[str]:
        fallback = [
            "Australia", "Botswana", "Brazil", "Canada", "China", "France", "Germany",
            "India", "Italy", "Japan", "Portugal", "Spain", "United Kingdom",
            "United States"
        ]

        try:
            response = requests.get(
                "https://restcountries.com/v3.1/all?fields=name",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            countries = []
            for item in data:
                name = item.get("name", {}).get("common", "")
                name = safe_text(name, fallback="")
                if name:
                    countries.append(name)

            countries = sorted(set(countries))
            return countries if countries else fallback
        except Exception:
            return fallback

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

    @st.cache_data(show_spinner=False)
    def search_places(country: str, city_query: str, region_query: str = "") -> list[dict]:
        query_parts = [city_query.strip(), region_query.strip(), country.strip()]
        query = ", ".join(part for part in query_parts if part)

        if not query:
            return []

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 10,
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

            places = []
            for item in results:
                address = item.get("address", {})

                found_country = safe_text(address.get("country", country))
                found_region = safe_text(
                    address.get("state")
                    or address.get("region")
                    or address.get("county")
                    or ""
                )
                found_city = safe_text(
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or address.get("municipality")
                    or city_query
                )

                label_parts = [found_city]
                if found_region and found_region != found_city:
                    label_parts.append(found_region)
                if found_country:
                    label_parts.append(found_country)

                places.append({
                    "label": " | ".join(part for part in label_parts if part),
                    "latitude": float(item["lat"]),
                    "longitude": float(item["lon"]),
                    "country": found_country,
                    "city": found_city,
                })

            unique_places = []
            seen = set()
            for place in places:
                key = (
                    round(place["latitude"], 5),
                    round(place["longitude"], 5),
                    place["label"],
                )
                if key not in seen:
                    seen.add(key)
                    unique_places.append(place)

            return unique_places
        except Exception:
            return []

    country_options = get_country_list()

    if "ai_settings" not in st.session_state:
        st.session_state.ai_settings = {
            "latitude": 38.7223,
            "longitude": -9.1393,
            "zoom": 11,
            "country": "Portugal",
            "city": "Lisbon",
        }

    if "sync_from_settings" not in st.session_state:
        st.session_state.sync_from_settings = True

    if (
        "lat_input" not in st.session_state
        or "lon_input" not in st.session_state
        or "zoom_input" not in st.session_state
        or "place_country" not in st.session_state
        or "place_region" not in st.session_state
        or "place_city_query" not in st.session_state
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
        st.session_state.place_region = ""
        st.session_state.place_city_query = "" if settings["city"] == "Unknown" else settings["city"]

        st.session_state.sync_from_settings = False

    if "location_mode" not in st.session_state:
        st.session_state.location_mode = "By coordinates"

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
                            "city": city,
                        }
                        st.session_state.sync_from_settings = True
                        st.rerun()
                except ValueError:
                    st.error("Latitude and longitude must be valid numbers.")

        else:
            st.selectbox("Country", options=country_options, key="place_country")
            st.text_input("Region (optional)", key="place_region")
            st.text_input("City", key="place_city_query")

            city_results = []
            if st.session_state.place_city_query.strip():
                city_results = search_places(
                    st.session_state.place_country,
                    st.session_state.place_city_query,
                    st.session_state.place_region,
                )

            if city_results:
                selected_idx = st.selectbox(
                    "Choose a location",
                    options=range(len(city_results)),
                    format_func=lambda i: city_results[i]["label"],
                )

                selected_place = city_results[selected_idx]

                st.text_input("Latitude", value=f"{selected_place['latitude']:.4f}", disabled=True)
                st.text_input("Longitude", value=f"{selected_place['longitude']:.4f}", disabled=True)

                if st.button("Use selected place", use_container_width=True):
                    st.session_state.ai_settings = {
                        "latitude": selected_place["latitude"],
                        "longitude": selected_place["longitude"],
                        "zoom": int(st.session_state.zoom_input),
                        "country": selected_place["country"],
                        "city": selected_place["city"],
                    }
                    st.session_state.sync_from_settings = True
                    st.rerun()

            elif st.session_state.place_city_query.strip():
                st.info("No city options found for that search.")

    settings = st.session_state.ai_settings

    st.markdown("""
    <div class="okavango-hero">
        <h1>🛰️ AI Workflow</h1>
        <p>Select the area using coordinates or by choosing country and city.</p>
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