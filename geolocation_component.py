from pathlib import Path

import streamlit.components.v1 as components


LOCATION_COMPONENT = components.declare_component(
    "browser_geolocation",
    path=str(Path(__file__).resolve().parent / "components" / "geolocation"),
)
