import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

import pandas as pd
import pydeck as pdk
import streamlit as st
from geolocation_component import LOCATION_COMPONENT


DATA_DIR = Path(__file__).resolve().parents[1]
DISTRICT_BOUNDARIES_PATH = DATA_DIR / "assets" / "nepal_districts.geojson"
MISSING = "N/A"
PAGE_SIZE = 8
MAP_TYPE_COLORS = (
    (8, 145, 178),
    (220, 38, 38),
    (124, 58, 237),
    (22, 163, 74),
    (234, 88, 12),
    (219, 39, 119),
    (37, 99, 235),
    (161, 98, 7),
    (13, 148, 136),
    (71, 85, 105),
)
MAP_STYLES = {
    "Light": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Streets": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    "Dark": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
}
DISTRICT_ALIASES = {
    "CHITAWAN": ("Chitwan",),
    "DHANUSHA": ("Dhanusa",),
    "KABHREPALANCHOK": ("Kavre", "Kavrepalanchok"),
    "KAPILBASTU": ("Kapilvastu",),
    "MAKAWANPUR": ("Makwanpur",),
    "NAWALPARASI4": ("Nawalpur", "Nawalparasi"),
    "NAWALPARASI5": ("Parasi", "Nawalparasi"),
    "RUKUM5": ("Rukum",),
    "RUKUM6": ("Rukum",),
    "TANAHU": ("Tanahun",),
}

st.set_page_config(page_title="Nearby map | CollegeNP", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f5f7fa; }
    [data-testid="stAppViewContainer"] > .main { padding-top: 1.2rem; }
    h1, h2, h3 { color: #075985; font-family: Georgia, serif; }
    .nearby-subtitle { color: #64748b; margin-top: -.5rem; }
    .nearby-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
        margin: .7rem 0; padding: .9rem;
    }
    .nearby-card img {
        border: 1px solid #e2e8f0; border-radius: 7px; float: left;
        height: 68px; margin: 0 .8rem .5rem 0; object-fit: contain;
        padding: 3px; width: 68px;
    }
    .nearby-name { color: #0f172a; font-size: 1rem; font-weight: 700; }
    .nearby-meta { color: #64748b; font-size: .87rem; margin-top: .3rem; }
    .nearby-card::after { clear: both; content: ""; display: block; }
    .filter-summary {
        color: #64748b; font-size: .88rem; line-height: 1.5;
        overflow-wrap: anywhere; padding: .35rem 0;
    }
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_sticky_header) {
        background: #f5f7fa; border-bottom: 1px solid #e2e8f0;
        padding: .45rem 0 .65rem; position: sticky; top: 0; z-index: 10;
    }
    .st-key-nearby_sticky_header h1 {
        font-size: 1.6rem !important; margin: 0 0 .35rem;
    }
    .st-key-nearby_results_scroll .stElementContainer:has(.nearby-results-sticky) {
        background: #f5f7fa; padding: .25rem 0 .55rem; position: sticky;
        top: 0; z-index: 5;
    }
    .nearby-results-sticky h3 { margin: 0 0 .25rem; }
    .nearby-results-sticky p { color: #64748b; margin: 0; }
    .st-key-nearby_results_scroll {
        height: calc(100vh - 12rem); min-height: 20rem;
        overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain;
        padding: 0 .55rem .75rem 0; scrollbar-gutter: stable;
    }
    .st-key-nearby_map_panel { overflow: visible; position: relative; }
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
        position: sticky; top: 11rem; z-index: 4;
    }
    .stApp:has(.nearby-map-zoomed) [data-testid="stHeader"] { display: none; }
    .stApp:has(.nearby-map-zoomed) [data-testid="stMainBlockContainer"] {
        max-width: none; padding: 0 !important;
    }
    .stApp:has(.nearby-map-zoomed) [data-testid="stMainBlockContainer"]
    > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:not(:has(.st-key-nearby_map_panel)) {
        display: none !important;
    }
    .stApp:has(.nearby-map-zoomed) [data-testid="stMainBlockContainer"]
    > [data-testid="stVerticalBlock"]
    > [data-testid="stElementContainer"]:not(:has(.st-key-nearby_map_panel)) {
        display: none !important;
    }
    .stApp:has(.nearby-map-zoomed) .stHorizontalBlock:has(.st-key-nearby_map_panel) {
        width: 100%;
    }
    .stApp:has(.nearby-map-zoomed) .stHorizontalBlock:has(.st-key-nearby_map_panel)
    > [data-testid="stColumn"]:not(:has(.st-key-nearby_map_panel)) {
        display: none;
    }
    .stApp:has(.nearby-map-zoomed) .stHorizontalBlock:has(.st-key-nearby_map_panel)
    > [data-testid="stColumn"]:has(.st-key-nearby_map_panel) {
        flex: 1 1 100%; max-width: 100%; width: 100%;
    }
    .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
    .stHorizontalBlock:has(.st-key-nearby_map_panel)
    > [data-testid="stColumn"]:not(:has(.st-key-nearby_map_panel)) {
        background: #fff; box-shadow: 2px 0 14px rgb(15 23 42 / 14%);
        box-sizing: border-box; display: block !important; height: 100dvh;
        inset: 0 auto 0 0; max-width: 360px; min-width: 0;
        overflow-x: hidden; overflow-y: auto; padding: 1rem;
        position: fixed; width: 360px;
        z-index: 55;
    }
    .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
    .st-key-nearby_results_scroll {
        height: auto !important; max-height: none !important; min-height: 0 !important;
        overflow: visible !important;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_results_handle {
        height: 44px; max-width: 28px; min-width: 28px; pointer-events: none;
        position: fixed; top: 50%; transform: translateY(-50%); width: 28px;
        z-index: 80;
    }
    .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
    .st-key-nearby_results_handle { left: 348px; }
    .stApp:has(.nearby-map-zoomed):not(:has(.nearby-results-panel-open))
    .st-key-nearby_results_handle { left: 0; }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_results_handle button {
        background: #fff; border: 1px solid #cbd5e1; border-left: 0;
        border-radius: 0 8px 8px 0; box-shadow: 2px 2px 8px rgb(15 23 42 / 16%);
        height: 44px; min-height: 44px; padding: 0; pointer-events: auto;
        width: 28px;
    }
    .stApp:has(.nearby-map-zoomed)
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
        background: #f5f7fa; height: 100dvh; inset: 0; overflow: auto;
        padding: 1rem; position: fixed; width: 100vw; z-index: 50;
    }
    .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
        left: 360px; width: calc(100vw - 360px);
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_panel {
        height: 100%; min-height: 100dvh; position: relative;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar {
        align-items: center; background: #fff; border: 1px solid #e2e8f0;
        border-radius: 12px; box-shadow: 0 4px 16px rgb(15 23 42 / 16%);
        display: flex; gap: .5rem; left: 1rem; padding: .45rem .75rem;
        position: absolute; top: 1rem; z-index: 25;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar h3 {
        margin: 0;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar [data-testid="stHorizontalBlock"] {
        align-items: center; gap: .5rem;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_panel
    [data-testid="stElementContainer"]:has([data-testid="stDeckGlJsonChart"]) {
        height: calc(100dvh - 5rem) !important; min-height: 32rem;
    }
    .stApp:has(.nearby-map-zoomed) [data-testid="stDeckGlJsonChart"] {
        height: calc(100dvh - 5rem) !important; min-height: 32rem;
    }
    .stApp:has(.nearby-map-zoomed)
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_filter_sidebar) {
        height: 100%; min-height: 0; width: 100%;
    }
    .st-key-nearby_filter_sidebar {
        box-sizing: border-box; display: flex; flex-direction: column;
        height: calc(100dvh - 2rem); overflow: hidden;
    }
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_filter_sidebar_header) {
        flex: 0 0 auto;
    }
    .st-key-nearby_filter_sidebar_header [data-testid="stHorizontalBlock"] {
        align-items: center; flex-wrap: nowrap !important; gap: .35rem;
    }
    .st-key-nearby_filter_sidebar_header [data-testid="stColumn"] {
        min-width: 0 !important;
    }
    .st-key-nearby_filter_sidebar_header [data-testid="stColumn"]:nth-child(1) {
        flex: 0 0 12% !important;
    }
    .st-key-nearby_filter_sidebar_header [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 38% !important;
    }
    .st-key-nearby_filter_sidebar_header [data-testid="stColumn"]:nth-child(3),
    .st-key-nearby_filter_sidebar_header [data-testid="stColumn"]:nth-child(4) {
        flex: 0 0 22% !important;
    }
    .st-key-nearby_filter_sidebar_header h3 {
        font-family: inherit; font-size: 1.1rem; margin: 0;
    }
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_filter_sidebar_body) {
        flex: 1 1 auto; min-height: 0; overflow-x: hidden; overflow-y: auto;
    }
    .st-key-nearby_filter_sidebar h2 { margin: 0; }
    .filter-group-heading {
        border-bottom: 1px solid #e2e8f0; color: #0f172a;
        font-size: 1.05rem; font-weight: 700;
        margin: .7rem 0 .9rem; padding-bottom: .5rem;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar {
        max-width: calc(100vw - 2rem);
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar iframe {
        border: 0; height: 48px; max-width: 100%; width: 100%;
    }
    .stApp:not(:has(.nearby-map-zoomed))
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_layer_switcher) {
        display: none;
    }
    .stApp:has(.nearby-map-zoomed)
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_layer_switcher) {
        background: #fff; border: 1px solid #cbd5e1; border-radius: 10px;
        bottom: 10rem; box-shadow: 0 3px 12px rgb(15 23 42 / 18%);
        padding: .45rem; position: fixed; right: 1rem; width: 10rem; z-index: 70;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_layer_switcher [data-testid="stSelectbox"] {
        margin: 0;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_layer_switcher label {
        display: none;
    }
    .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar iframe {
        bottom: 4.75rem; height: 48px; position: fixed; right: 1rem;
        width: 11rem; z-index: 70;
    }
    .stApp:has(.nearby-map-zoomed) [data-testid="stDeckGlJsonChartZoomButton"] {
        bottom: 4.75rem !important; height: auto !important; left: auto !important;
        right: 1rem !important; top: auto !important; width: auto !important;
    }
    .st-key-nearby_map_legend {
        bottom: 2.5rem; left: .75rem; max-width: min(22rem, calc(100% - 1.5rem));
        position: absolute; z-index: 15;
    }
    .nearby-map-legend {
        background: rgb(255 255 255 / 96%); border: 1px solid #cbd5e1;
        border-radius: 10px; box-shadow: 0 3px 12px rgb(15 23 42 / 16%);
        color: #0f172a; display: flex; flex-wrap: wrap; gap: .45rem .8rem;
        max-height: 8rem; overflow-y: auto; padding: .6rem .75rem;
    }
    .nearby-map-legend-title {
        flex-basis: 100%; font-size: .78rem; font-weight: 700;
    }
    .nearby-map-legend-item {
        align-items: center; display: inline-flex; font-size: .76rem; gap: .35rem;
    }
    .nearby-map-legend-dot {
        border: 1px solid rgb(15 23 42 / 15%); border-radius: 50%;
        display: inline-block; flex: 0 0 11px; height: 11px; width: 11px;
    }
    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 1.25rem; padding-right: 1.25rem;
        }
        .st-key-nearby_results_scroll {
            height: auto; max-height: 70vh; min-height: 0;
        }
        .stHorizontalBlock:has(.st-key-nearby_results_scroll) {
            flex-direction: column;
        }
        .stHorizontalBlock:has(.st-key-nearby_results_scroll)
        > [data-testid="stColumn"] {
            flex: 1 1 100%; max-width: 100%; min-width: 0; width: 100%;
        }
        .stHorizontalBlock:has(.st-key-nearby_results_scroll)
        > [data-testid="stColumn"]:has(.st-key-nearby_map_panel) {
            order: -1;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
            position: static;
        }
        .stApp:has(.nearby-map-zoomed)
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
            height: 100dvh; inset: 0; overflow: hidden; padding: .5rem;
            position: fixed; width: 100vw;
        }
        .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
        .stHorizontalBlock:has(.st-key-nearby_map_panel)
        > [data-testid="stColumn"]:not(:has(.st-key-nearby_map_panel)) {
            border-radius: 0 14px 14px 0; height: 100dvh; inset: 0 auto 0 0;
            max-width: min(24rem, 88vw); padding: .75rem;
            overflow-y: auto;
            width: min(24rem, 88vw); z-index: 58;
        }
        .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
            left: 0; width: 100vw;
        }
        .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
        .st-key-nearby_results_handle {
            left: calc(min(24rem, 88vw) - 12px);
        }
        .stApp:has(.nearby-map-zoomed):not(:has(.nearby-results-panel-open))
        .st-key-nearby_results_handle { left: 0; }
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar {
            left: .5rem; top: .5rem;
        }
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_panel
        [data-testid="stElementContainer"]:has([data-testid="stDeckGlJsonChart"]),
        .stApp:has(.nearby-map-zoomed) [data-testid="stDeckGlJsonChart"] {
            height: calc(100dvh - 4rem) !important; min-height: 24rem;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_sticky_header) {
            top: 0;
        }
        .st-key-nearby_filter_sidebar {
            height: calc(100dvh - 1.5rem);
        }
    }
    @media (max-width: 600px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: .65rem; padding-right: .65rem;
        }
        [data-testid="stAppViewContainer"] > .main { padding-top: .65rem; }
        .stApp:has(.nearby-map-zoomed)
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
            padding: .25rem;
        }
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar {
            left: .25rem; max-width: calc(100vw - .5rem);
            padding: .35rem; right: .25rem; top: .25rem;
        }
        .stApp:has(.nearby-map-zoomed)
        .st-key-nearby_map_toolbar [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap; gap: .25rem;
        }
        .stApp:has(.nearby-map-zoomed)
        .st-key-nearby_map_toolbar [data-testid="stColumn"] {
            flex: 1 1 calc(50% - .25rem); min-width: 0;
        }
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar h3 {
            font-size: 1.05rem;
        }
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_toolbar iframe {
            bottom: 4.5rem; height: 48px; min-width: 0; right: .5rem;
            width: 11rem;
        }
        .stApp:has(.nearby-map-zoomed)
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_layer_switcher) {
            bottom: 9.5rem; right: .5rem; width: 9.5rem;
        }
        .stApp:has(.nearby-map-zoomed) [data-testid="stDeckGlJsonChartZoomButton"] {
            bottom: 4.5rem !important; right: 2.1rem !important;
        }
        .st-key-nearby_map_legend {
            bottom: 1.5rem; left: .4rem;
            max-width: min(18rem, calc(100% - .8rem));
        }
        .nearby-map-legend { gap: .35rem .6rem; max-height: 6.5rem; padding: .5rem; }
        .nearby-map-legend-item { font-size: .7rem; }
        .stApp:has(.nearby-map-zoomed) [data-testid="stDeckGlJsonChart"],
        .stApp:has(.nearby-map-zoomed) .st-key-nearby_map_panel
        [data-testid="stElementContainer"]:has([data-testid="stDeckGlJsonChart"]) {
            height: calc(100dvh - 4.25rem) !important; min-height: 20rem;
        }
        .st-key-nearby_results_scroll { max-height: none; padding-right: 0; }
        .stApp:has(.nearby-map-zoomed.nearby-results-panel-open)
        .st-key-nearby_results_scroll { height: auto !important; }
        .nearby-card { padding: .7rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_sheet(workbook_path: str, sheet_name: str) -> pd.DataFrame:
    dataframe = pd.read_excel(
        workbook_path,
        sheet_name=sheet_name,
        dtype=str,
        engine="openpyxl",
    )
    dataframe = dataframe.apply(
        lambda column: column.map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    )
    return dataframe.fillna(MISSING).replace("", MISSING)


@st.cache_data(show_spinner=False)
def load_district_boundaries(path: str) -> dict:
    boundaries = json.loads(Path(path).read_text(encoding="utf-8"))
    features = boundaries.get("features", [])
    if boundaries.get("type") != "FeatureCollection" or len(features) != 77:
        raise ValueError(f"Expected 77 Nepal district polygons in {path}.")
    return boundaries


def normalize_place(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def selected_district_features(
    boundaries: dict, selected_places: list[str]
) -> list[dict]:
    selected_names = {normalize_place(value) for value in selected_places}
    matches = []
    for feature in boundaries["features"]:
        district = feature["properties"]["district"]
        candidates = {normalize_place(district)}
        candidates.update(
            normalize_place(alias) for alias in DISTRICT_ALIASES.get(district, ())
        )
        if candidates.intersection(selected_names):
            matches.append(feature)
    return matches


def geojson_positions(geometry: dict) -> list[tuple[float, float]]:
    positions = []
    pending = [geometry["coordinates"]]
    while pending:
        coordinate = pending.pop()
        if (
            isinstance(coordinate, list)
            and len(coordinate) >= 2
            and isinstance(coordinate[0], (int, float))
            and isinstance(coordinate[1], (int, float))
        ):
            positions.append((float(coordinate[0]), float(coordinate[1])))
        elif isinstance(coordinate, list):
            pending.extend(coordinate)
    return positions


def available_values(series: pd.Series, split_commas: bool = False) -> list[str]:
    values = set()
    for value in series:
        if value == MISSING:
            continue
        parts = value.split(",") if split_commas else [value]
        values.update(
            part.strip()
            for part in parts
            if part.strip() and part.strip() != MISSING
        )
    return sorted(values, key=str.casefold)


def token_match(series: pd.Series, selected: list[str]) -> pd.Series:
    selected_values = {value.casefold() for value in selected}
    return series.map(
        lambda value: bool(
            selected_values.intersection(
                token.strip().casefold() for token in str(value).split(",")
            )
        )
    )


def text_match(series: pd.Series, selected: list[str]) -> pd.Series:
    selected_values = [value.casefold() for value in selected]
    return series.map(
        lambda value: any(option in str(value).casefold() for option in selected_values)
    )


def is_safe_web_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def social_link_columns(columns: pd.Index) -> list[tuple[str, str]]:
    networks = {
        "facebook": "Facebook",
        "instagram": "Instagram",
        "linkedin": "LinkedIn",
        "twitter": "X / Twitter",
        "youtube": "YouTube",
        "tiktok": "TikTok",
    }
    return [
        (column, label)
        for column in columns
        for key, label in networks.items()
        if key in column.casefold()
    ]


def map_tooltip_html(social_columns: list[tuple[str, str]]) -> str:
    social_links = "".join(
        f'<a href="{{social_{index}_href}}">{{social_{index}_label}}</a>'
        for index, _ in enumerate(social_columns)
    ) or '<span>Social links: N/A</span>'
    return (
        '<div style="background:#fff;border:1px solid #cbd5e1;border-radius:12px;'
        'box-shadow:0 8px 24px #0f172a33;color:#0f172a;font:13px/1.45 sans-serif;'
        'min-width:230px;max-width:310px;padding:12px">'
        '<div style="align-items:center;display:flex;gap:10px">'
        '<img src="{logo}" alt="" referrerpolicy="no-referrer" '
        'style="width:56px;height:56px;object-fit:contain;border-radius:8px;'
        'border:1px solid #e2e8f0;background:#fff">'
        '<div><strong style="font-size:15px">{name}</strong>'
        '<div style="color:#64748b">{city}</div></div></div>'
        '<div style="color:#475569;margin-top:5px">{institution_type}</div>'
        '<div style="color:#64748b;margin-top:8px">{address}</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px">'
        '<a href="{email_href}">Email: {email}</a>'
        '<a href="{website_href}" target="_blank" rel="noopener noreferrer">'
        '{website_label}</a>'
        f"{social_links}"
        "</div>"
        '<div style="background:#075985;border-radius:7px;color:#fff;'
        'font-weight:700;margin-top:11px;padding:8px;text-align:center">'
        "Click map pin to open listing details →</div></div>"
    )


def reset_results_page() -> None:
    st.session_state["nearby_page"] = 1


def filter_state_keys(dataset_key: str) -> dict[str, str]:
    return {
        name: f"nearby_filter_{name}_{dataset_key}"
        for name in (
            "city",
            "stream",
            "affiliation",
            "course_type",
            "fee",
            "institution_type",
            "duration",
        )
    }


def begin_filter_edit(keys: dict[str, str]) -> None:
    filter_view_open = st.session_state.get("nearby_filter_sidebar_open", False)
    if filter_view_open:
        save_filter_draft(keys)
    for state_key in keys.values():
        draft_key = f"{state_key}_draft"
        saved_key = f"{state_key}_draft_values"
        if saved_key not in st.session_state:
            st.session_state[saved_key] = list(st.session_state.get(state_key, []))
        st.session_state[draft_key] = list(st.session_state[saved_key])
    st.session_state["nearby_filter_sidebar_open"] = True
    st.session_state["nearby_results_panel_open"] = True


def save_filter_draft(keys: dict[str, str]) -> None:
    for state_key in keys.values():
        draft_key = f"{state_key}_draft"
        saved_key = f"{state_key}_draft_values"
        st.session_state[saved_key] = list(
            st.session_state.get(draft_key, st.session_state.get(state_key, []))
        )


def clear_draft_filters(keys: dict[str, str]) -> None:
    for state_key in keys.values():
        st.session_state[f"{state_key}_draft"] = []
        st.session_state[f"{state_key}_draft_values"] = []


def back_to_results(keys: dict[str, str]) -> None:
    save_filter_draft(keys)
    st.session_state["nearby_filter_sidebar_open"] = False


def apply_filter_draft(keys: dict[str, str]) -> None:
    for state_key in keys.values():
        draft = list(st.session_state.get(f"{state_key}_draft", []))
        st.session_state[state_key] = draft
        st.session_state[f"{state_key}_draft_values"] = draft
    st.session_state["nearby_filter_sidebar_open"] = False
    st.session_state["nearby_results_panel_open"] = True
    st.session_state["nearby_page"] = 1


def enter_zoom_map() -> None:
    st.session_state["nearby_zoom_map"] = True
    st.session_state["nearby_results_panel_open"] = True
    st.session_state["nearby_filter_sidebar_open"] = False


def exit_zoom_map(keys: dict[str, str]) -> None:
    if st.session_state.get("nearby_filter_sidebar_open", False):
        save_filter_draft(keys)
    st.session_state["nearby_zoom_map"] = False
    st.session_state["nearby_results_panel_open"] = False
    st.session_state["nearby_filter_sidebar_open"] = False


def toggle_results_panel(keys: dict[str, str]) -> None:
    filter_view_open = st.session_state.get("nearby_filter_sidebar_open", False)
    if filter_view_open:
        save_filter_draft(keys)
    panel_open = not st.session_state.get("nearby_results_panel_open", True)
    st.session_state["nearby_results_panel_open"] = panel_open
    if filter_view_open and panel_open:
        for state_key in keys.values():
            st.session_state[f"{state_key}_draft"] = list(
                st.session_state.get(f"{state_key}_draft_values", [])
            )


def show_filter_sidebar() -> None:
    with st.container(key="nearby_filter_sidebar"):
        with st.container(key="nearby_filter_sidebar_header"):
            back_column, heading_column, clear_column, done_column = st.columns(
                [0.7, 1.7, 1, 1], vertical_alignment="center"
            )
            back_column.button(
                "←",
                key=f"back_nearby_filters_{directory_key}",
                help="Back to results",
                on_click=back_to_results,
                args=(filter_keys,),
                width="stretch",
            )
            heading_column.markdown("### Filters")
            clear_column.button(
                "Clear",
                key=f"clear_nearby_filters_{directory_key}",
                on_click=clear_draft_filters,
                args=(filter_keys,),
                width="stretch",
            )
            done_column.button(
                "Done",
                key=f"apply_nearby_filters_{directory_key}",
                type="primary",
                on_click=apply_filter_draft,
                args=(filter_keys,),
                width="stretch",
            )
        with st.container(key="nearby_filter_sidebar_body"):
            st.markdown(
                '<div class="filter-group-heading">Location</div>',
                unsafe_allow_html=True,
            )
            st.multiselect(
                "⌖ City / District",
                city_options,
                key=f"{filter_keys['city']}_draft",
                placeholder="Choose options",
            )
            st.markdown(
                '<div class="filter-group-heading">Study options</div>',
                unsafe_allow_html=True,
            )
            st.multiselect(
                "▤ Main stream",
                sorted(stream_options, key=str.casefold),
                key=f"{filter_keys['stream']}_draft",
                placeholder="Choose options",
            )
            st.multiselect(
                "✓ Affiliated by",
                sorted(affiliation_options, key=str.casefold),
                key=f"{filter_keys['affiliation']}_draft",
                placeholder="Choose options",
            )
            st.multiselect(
                "▤ Course type",
                course_type_options,
                key=f"{filter_keys['course_type']}_draft",
                placeholder="Choose options",
            )
            st.multiselect(
                "₹ Course fee",
                fee_options,
                key=f"{filter_keys['fee']}_draft",
                placeholder="Choose options",
                disabled=not fee_options,
                help=(
                    "Course fee data is not available in this workbook."
                    if not fee_options
                    else None
                ),
            )
            if not fee_options:
                st.caption("Course fee data is not available in this workbook.")
            st.multiselect(
                f"▥ Type of {entity_singular}",
                institution_type_options,
                key=f"{filter_keys['institution_type']}_draft",
                placeholder="Choose options",
            )
            st.multiselect(
                "▦ Duration",
                duration_options,
                key=f"{filter_keys['duration']}_draft",
                placeholder="Choose options",
            )


workbooks = sorted(
    path
    for path in DATA_DIR.glob("collegenp_*_and_courses.xlsx")
    if not path.name.startswith("~$")
)
if not workbooks:
    st.warning(f"No CollegeNP workbooks found in {DATA_DIR}.")
    st.stop()

labels = {
    path: "Colleges" if "colleges" in path.stem else "Schools"
    for path in workbooks
}
preferred_workbook = st.session_state.get("selected_directory")
default_index = workbooks.index(preferred_workbook) if preferred_workbook in workbooks else 0
selected_workbook = st.selectbox(
    "Directory",
    workbooks,
    index=default_index,
    format_func=lambda path: labels[path],
    key="nearby_directory",
    on_change=reset_results_page,
)
entity_sheet = next(
    sheet
    for sheet in pd.ExcelFile(selected_workbook, engine="openpyxl").sheet_names
    if sheet != "Courses"
)
entity_singular = "college" if entity_sheet == "Colleges" else "school"
directory = load_sheet(str(selected_workbook), entity_sheet)
courses = load_sheet(str(selected_workbook), "Courses")
name_column = next(
    (column for column in directory.columns if column.lower().endswith("name")),
    directory.columns[0],
)
course_entity_column = courses.columns[0]
city_column = "City / District"
stream_column = "Stream / Category"
affiliation_column = "Affiliated By"
type_column = next(
    (column for column in directory.columns if column.lower().endswith("type")),
    None,
)
course_stream_column = "Stream / Specialization"
course_affiliation_column = "Affiliation Body for the specific course"
course_type_column = "Course Type"
duration_column = "Duration"
fee_columns = [
    column
    for column in ("Total Fee (with currency/amount)", "Total Fee")
    if column in courses
]
directory_key = selected_workbook.stem
filter_keys = filter_state_keys(directory_key)

city_options = (
    available_values(directory[city_column]) if city_column in directory else []
)
stream_options = set(
    available_values(directory[stream_column], split_commas=True)
    if stream_column in directory
    else []
)
if course_stream_column in courses:
    stream_options.update(
        available_values(courses[course_stream_column], split_commas=True)
    )
affiliation_options = set(
    available_values(directory[affiliation_column])
    if affiliation_column in directory
    else []
)
if course_affiliation_column in courses:
    affiliation_options.update(available_values(courses[course_affiliation_column]))
course_type_options = (
    available_values(courses[course_type_column])
    if course_type_column in courses
    else []
)
fee_options = sorted(
    {
        value
        for column in fee_columns
        for value in available_values(courses[column])
    },
    key=str.casefold,
)
institution_type_options = (
    available_values(directory[type_column]) if type_column else []
)
duration_options = (
    available_values(courses[duration_column])
    if duration_column in courses
    else []
)

selected_cities = st.session_state.get(filter_keys["city"], [])
selected_streams = st.session_state.get(filter_keys["stream"], [])
selected_affiliations = st.session_state.get(filter_keys["affiliation"], [])
selected_course_types = st.session_state.get(filter_keys["course_type"], [])
selected_fees = st.session_state.get(filter_keys["fee"], [])
selected_types = st.session_state.get(filter_keys["institution_type"], [])
selected_durations = st.session_state.get(filter_keys["duration"], [])
selected_filter_count = sum(
    bool(values)
    for values in (
        selected_cities,
        selected_streams,
        selected_affiliations,
        selected_course_types,
        selected_fees,
        selected_types,
        selected_durations,
    )
)
st.page_link("streamlit_app.py", label="← Back to directory")
st.markdown(
'<div class="nearby-subtitle">Filter by location and study options, then explore '
'matching listings on the map.</div>',
unsafe_allow_html=True,
)
zoom_map_active = st.session_state.get("nearby_zoom_map", False)
search_key = f"nearby_search_{directory_key}"
search_text = str(st.session_state.get(search_key, ""))
with st.container(key="nearby_sticky_header"):
    st.title(f"Find {entity_sheet.lower()} nearby")
    if not zoom_map_active:
        search_text = st.text_input(
            "Search",
            placeholder="Search by name, city, or address",
            key=search_key,
            on_change=reset_results_page,
            label_visibility="collapsed",
        )

    active_filters = []
    for label, values in (
        ("City", selected_cities),
        ("Stream", selected_streams),
        ("Affiliated by", selected_affiliations),
        ("Course type", selected_course_types),
        ("Course fee", selected_fees),
        ("Institution type", selected_types),
        ("Duration", selected_durations),
    ):
        if values:
            active_filters.append(f"{label}: {', '.join(values)}")
    st.markdown(
        '<div class="filter-summary">'
        + (
            escape(" · ".join(active_filters))
            if active_filters
            else "Add filters to narrow listings on the map."
        )
        + "</div>",
        unsafe_allow_html=True,
    )


results_column, map_column = st.columns([0.46, 0.54], gap="medium")

with results_column:
    filter_panel_open = zoom_map_active and st.session_state.get(
        "nearby_filter_sidebar_open", False
    )
    if zoom_map_active and not filter_panel_open:
        search_text = st.text_input(
            "Search listings",
            placeholder="Search by name, city, or address",
            key=search_key,
            on_change=reset_results_page,
            label_visibility="collapsed",
        )
    profile_mask = pd.Series(True, index=directory.index)
    if selected_cities and city_column in directory:
        profile_mask &= directory[city_column].isin(selected_cities)
    if selected_types and type_column:
        profile_mask &= directory[type_column].isin(selected_types)
    if search_text.strip():
        searchable_columns = [
            column
            for column in (
                name_column,
                city_column,
                "Address (Full location detail)",
            )
            if column in directory
        ]
        profile_mask &= directory[searchable_columns].apply(
            lambda column: column.str.contains(
                search_text.strip(), case=False, regex=False, na=False
            )
        ).any(axis=1)

    course_mask = pd.Series(True, index=courses.index)
    if selected_course_types and course_type_column in courses:
        course_mask &= courses[course_type_column].isin(selected_course_types)
    if selected_durations and duration_column in courses:
        course_mask &= courses[duration_column].isin(selected_durations)
    if selected_fees and fee_columns:
        fee_match = pd.Series(False, index=courses.index)
        for column in fee_columns:
            fee_match |= courses[column].isin(selected_fees)
        course_mask &= fee_match
    course_filters_active = bool(
        selected_course_types or selected_durations or selected_fees
    )
    eligible_course_names = set(courses.loc[course_mask, course_entity_column])
    if course_filters_active:
        profile_mask &= directory[name_column].isin(eligible_course_names)

    if selected_streams:
        profile_stream_match = (
            token_match(directory[stream_column], selected_streams)
            if stream_column in directory
            else pd.Series(False, index=directory.index)
        )
        if course_stream_column in courses:
            course_stream_match = token_match(
                courses[course_stream_column], selected_streams
            )
            stream_names = set(
                courses.loc[course_mask & course_stream_match, course_entity_column]
            )
        else:
            stream_names = set()
        profile_mask &= profile_stream_match | directory[name_column].isin(stream_names)

    if selected_affiliations:
        profile_affiliation_match = (
            text_match(directory[affiliation_column], selected_affiliations)
            if affiliation_column in directory
            else pd.Series(False, index=directory.index)
        )
        affiliation_course_match = (
            text_match(courses[course_affiliation_column], selected_affiliations)
            if course_affiliation_column in courses
            else pd.Series(False, index=courses.index)
        )
        affiliation_course_names = set(
            courses.loc[course_mask & affiliation_course_match, course_entity_column]
        )
        profile_mask &= (
            profile_affiliation_match
            | directory[name_column].isin(affiliation_course_names)
        )

    filtered = directory.loc[profile_mask].drop_duplicates().reset_index(drop=True)
    district_boundaries = load_district_boundaries(str(DISTRICT_BOUNDARIES_PATH))
    all_boundary_positions = [
        position
        for feature in district_boundaries["features"]
        for position in geojson_positions(feature["geometry"])
    ]
    min_longitude = min(position[0] for position in all_boundary_positions)
    max_longitude = max(position[0] for position in all_boundary_positions)
    min_latitude = min(position[1] for position in all_boundary_positions)
    max_latitude = max(position[1] for position in all_boundary_positions)
    boundary_padding = 0.1
    latitude_column = "Map Latitude"
    longitude_column = "Map Longitude"
    if latitude_column in filtered and longitude_column in filtered:
        filtered = filtered.assign(
            _latitude=pd.to_numeric(filtered[latitude_column], errors="coerce"),
            _longitude=pd.to_numeric(filtered[longitude_column], errors="coerce"),
        )
    else:
        filtered = filtered.assign(_latitude=float("nan"), _longitude=float("nan"))
    has_coordinates = (
        filtered["_latitude"].between(-90, 90)
        & filtered["_longitude"].between(-180, 180)
        & filtered["_latitude"].between(
            min_latitude - boundary_padding, max_latitude + boundary_padding
        )
        & filtered["_longitude"].between(
            min_longitude - boundary_padding, max_longitude + boundary_padding
        )
    )
    mapped = filtered.loc[has_coordinates].copy()

    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, st.session_state.get("nearby_page", 1)), total_pages)
    st.session_state["nearby_page"] = page
    page_rows = filtered.iloc[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    if filter_panel_open:
        show_filter_sidebar()
    else:
        with st.container(key="nearby_results_scroll"):
            if zoom_map_active and active_filters:
                st.markdown(
                    '<div class="filter-summary">'
                    + escape(" · ".join(active_filters))
                    + "</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<div class="nearby-results-sticky">'
                '<h3>Nearby listings</h3>'
                '<p>Map pins show listings with valid coordinates within Nepal.</p>'
                f'<p><strong>{len(filtered):,}</strong> matching listings</p>'
                "</div>",
                unsafe_allow_html=True,
            )

            for index, (_, listing) in enumerate(page_rows.iterrows()):
                name = str(listing.get(name_column, MISSING))
                city = str(listing.get(city_column, MISSING))
                address = str(listing.get("Address (Full location detail)", MISSING))
                logo = str(
                    listing.get(
                        "College Logo URL", listing.get("School Logo URL", MISSING)
                    )
                )
                logo_markup = (
                    f'<img src="{escape(logo, quote=True)}" alt="" loading="lazy" '
                    'referrerpolicy="no-referrer">'
                    if is_safe_web_url(logo)
                    else ""
                )
                listing_type = (
                    str(listing.get(type_column, MISSING)) if type_column else MISSING
                )
                location = " · ".join(
                    value for value in (city, address) if value != MISSING
                ) or "Location not listed"
                st.markdown(
                    f'<article class="nearby-card">{logo_markup}'
                    f'<div class="nearby-name">{escape(name)}</div>'
                    f'<div class="nearby-meta">{escape(location)}</div>'
                    f'<div class="nearby-meta">{escape(listing_type)}</div></article>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "View details",
                    key=f"nearby_detail_{selected_workbook.stem}_{(page - 1) * PAGE_SIZE + index}",
                    width="stretch",
                ):
                    st.session_state["detail_workbook"] = str(selected_workbook)
                    st.session_state["detail_profile"] = listing.drop(
                        labels=["_latitude", "_longitude"], errors="ignore"
                    ).to_dict()
                    st.switch_page("pages/listing_detail.py")

            if not len(filtered):
                st.info(
                    "No listings match these filters. Try a different search or remove a filter."
                )
            if total_pages > 1:
                previous_column, page_column, next_column = st.columns([1, 1, 1])
                if previous_column.button(
                    "←",
                    disabled=page == 1,
                    key=f"nearby_prev_{selected_workbook.stem}",
                ):
                    st.session_state["nearby_page"] = page - 1
                    st.rerun()
                page_column.caption(f"{page} / {total_pages}")
                if next_column.button(
                    "→",
                    disabled=page == total_pages,
                    key=f"nearby_next_{selected_workbook.stem}",
                ):
                    st.session_state["nearby_page"] = page + 1
                    st.rerun()

with map_column:
    with st.container(key="nearby_map_panel"):
        zoom_map = st.session_state.get("nearby_zoom_map", False)
        if zoom_map:
            zoom_marker_classes = ["nearby-map-zoomed"]
            if st.session_state.get("nearby_results_panel_open", True):
                zoom_marker_classes.append("nearby-results-panel-open")
            st.markdown(
                f'<span class="{" ".join(zoom_marker_classes)}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
        with st.container(key="nearby_map_toolbar"):
            if zoom_map:
                (
                    title_column,
                    filter_column,
                    location_column,
                    exit_column,
                ) = st.columns(
                    [1.3, 1.3, 1.3, .8], vertical_alignment="center"
                )
                title_column.subheader("Map")
                filter_column.button(
                    f"☷ All filters{f' · {selected_filter_count}' if selected_filter_count else ''}",
                    key=f"open_nearby_filters_{directory_key}",
                    on_click=begin_filter_edit,
                    args=(filter_keys,),
                    type="secondary",
                    width="stretch",
                )
                with location_column:
                    location_result = LOCATION_COMPONENT(
                        key=f"nearby_location_{directory_key}",
                        default=None,
                    )
                exit_column.button(
                    "Exit map",
                    key=f"exit_nearby_zoom_map_{directory_key}",
                    on_click=exit_zoom_map,
                    args=(filter_keys,),
                    type="secondary",
                    width="stretch",
                )
            else:
                title_column, location_column, zoom_column = st.columns(
                    [3.5, 2, 1.5], vertical_alignment="center"
                )
                title_column.subheader("Map")
                with location_column:
                    location_result = LOCATION_COMPONENT(
                        key=f"nearby_location_{directory_key}",
                        default=None,
                    )
                zoom_column.button(
                    "⛶ Zoom map",
                    key=f"zoom_nearby_map_{directory_key}",
                    on_click=enter_zoom_map,
                    type="secondary",
                    width="stretch",
                )
        if zoom_map:
            results_panel_open = st.session_state.get(
                "nearby_results_panel_open", True
            )
            with st.container(key="nearby_results_handle"):
                st.button(
                    "‹" if results_panel_open else "›",
                    key=f"toggle_nearby_results_{directory_key}",
                    help=(
                        "Hide results panel"
                        if results_panel_open
                        else "Show results panel"
                    ),
                    on_click=toggle_results_panel,
                    args=(filter_keys,),
                )
        if isinstance(location_result, dict):
            status = location_result.get("status")
            timestamp = location_result.get("timestamp")
            if timestamp != st.session_state.get("nearby_gps_timestamp"):
                st.session_state["nearby_gps_timestamp"] = timestamp
                st.session_state["nearby_gps_status"] = status
                if status == "success":
                    latitude = pd.to_numeric(
                        location_result.get("latitude"), errors="coerce"
                    )
                    longitude = pd.to_numeric(
                        location_result.get("longitude"), errors="coerce"
                    )
                    if (
                        pd.notna(latitude)
                        and pd.notna(longitude)
                        and -90 <= latitude <= 90
                        and -180 <= longitude <= 180
                    ):
                        st.session_state["nearby_user_location"] = {
                            "latitude": float(latitude),
                            "longitude": float(longitude),
                        }
                    else:
                        st.session_state["nearby_gps_status"] = "invalid"
        gps_status = st.session_state.get("nearby_gps_status")
        if gps_status and gps_status != "success":
            status_messages = {
                "denied": "Location permission was denied. Enable it in your browser settings to use this feature.",
                "unavailable": "Your location is currently unavailable.",
                "timeout": "The location request timed out. Try again.",
                "unsupported": "Geolocation is not supported by this browser.",
                "invalid": "The browser returned invalid location coordinates.",
            }
            st.warning(
                status_messages.get(
                    gps_status, "Could not determine your location. Try again."
                )
            )
        highlighted_districts = selected_district_features(
            district_boundaries, selected_cities
        )
        if mapped.empty:
            st.caption(
                "No matching listings have valid map coordinates. Add latitude "
                "and longitude values within Nepal to show map pins; district "
                "boundaries remain available for reference."
            )
        social_columns = social_link_columns(directory.columns)
        map_data = pd.DataFrame(
            {
                "name": mapped[name_column],
                "city": mapped[city_column]
                if city_column in mapped
                else MISSING,
                "address": mapped["Address (Full location detail)"]
                if "Address (Full location detail)" in mapped
                else MISSING,
                "institution_type": mapped[type_column]
                if type_column
                else MISSING,
                "longitude": mapped["_longitude"],
                "latitude": mapped["_latitude"],
                "email": mapped["Contact Email"]
                if "Contact Email" in mapped
                else MISSING,
                "website": mapped["Official Website URL"]
                if "Official Website URL" in mapped
                else MISSING,
                "logo": mapped.get(
                    "College Logo URL",
                    mapped.get("School Logo URL", pd.Series(MISSING, index=mapped.index)),
                ),
                "listing_index": mapped.index,
            }
        )
        map_data["email_href"] = map_data["email"].map(
            lambda value: f"mailto:{quote(str(value), safe='@.+-_')}"
            if value != MISSING
            else "#"
        )
        map_data["website_href"] = map_data["website"].map(
            lambda value: str(value) if is_safe_web_url(str(value)) else "#"
        )
        map_data["website_label"] = map_data["website"].map(
            lambda value: "Website"
            if is_safe_web_url(str(value))
            else "Website: N/A"
        )
        map_data["logo"] = map_data["logo"].map(
            lambda value: (
                str(value)
                if is_safe_web_url(str(value))
                else "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
            )
        )
        map_data["institution_type"] = map_data["institution_type"].map(
            lambda value: str(value).strip() or MISSING
        )
        type_categories = sorted(
            map_data["institution_type"].unique(),
            key=str.casefold,
        )
        type_colors = {
            category: MAP_TYPE_COLORS[index % len(MAP_TYPE_COLORS)]
            for index, category in enumerate(type_categories)
        }
        map_data["marker_color"] = map_data["institution_type"].map(type_colors)
        user_location = st.session_state.get("nearby_user_location")
        for index, (column, label) in enumerate(social_columns):
            social_values = mapped[column]
            map_data[f"social_{index}_href"] = social_values.map(
                lambda value: (
                    str(value) if is_safe_web_url(str(value)) else "#"
                )
            )
            map_data[f"social_{index}_label"] = social_values.map(
                lambda value: label if is_safe_web_url(str(value)) else f"{label}: N/A"
            )
        if type_categories:
            legend_items = "".join(
                '<span class="nearby-map-legend-item">'
                f'<span class="nearby-map-legend-dot" '
                f'style="background:rgb({color[0]} {color[1]} {color[2]})"></span>'
                f'{escape("Type not listed" if category == MISSING else category)}'
                "</span>"
                for category, color in type_colors.items()
            )
            if user_location:
                legend_items += (
                    '<span class="nearby-map-legend-item">'
                    '<span class="nearby-map-legend-dot" '
                    'style="background:rgb(220 38 38)"></span>Your location</span>'
                )
            with st.container(key="nearby_map_legend"):
                st.markdown(
                    '<div class="nearby-map-legend">'
                    '<span class="nearby-map-legend-title">Listing type</span>'
                    f"{legend_items}</div>",
                    unsafe_allow_html=True,
                )
        marker_positions = list(
            zip(map_data["longitude"].tolist(), map_data["latitude"].tolist())
        )
        fit_positions = [
            position
            for feature in highlighted_districts
            for position in geojson_positions(feature["geometry"])
        ]
        if not fit_positions:
            fit_positions = marker_positions
        if not fit_positions:
            fit_positions = all_boundary_positions
        if user_location:
            initial_view_state = pdk.ViewState(
                latitude=user_location["latitude"],
                longitude=user_location["longitude"],
                zoom=13,
            )
        elif len(set(fit_positions)) > 1:
            initial_view_state = pdk.data_utils.compute_view(
                fit_positions, view_proportion=1
            )
        else:
            longitude, latitude = fit_positions[0]
            initial_view_state = pdk.ViewState(
                latitude=latitude, longitude=longitude, zoom=11
            )

        map_layers = [
            pdk.Layer(
                "GeoJsonLayer",
                data=district_boundaries,
                get_fill_color=[255, 255, 255, 0],
                get_line_color=[100, 116, 139, 150],
                get_line_width=1,
                line_width_min_pixels=1,
                pickable=False,
            )
        ]
        if highlighted_districts:
            map_layers.append(
                pdk.Layer(
                    "GeoJsonLayer",
                    data={
                        "type": "FeatureCollection",
                        "features": highlighted_districts,
                    },
                    get_fill_color=[8, 145, 178, 35],
                    get_line_color=[8, 145, 178, 230],
                    get_line_width=2,
                    line_width_min_pixels=2,
                    pickable=False,
                )
            )
        if user_location:
            map_layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=[user_location],
                    get_position="[longitude, latitude]",
                    get_radius=900,
                    radius_min_pixels=8,
                    radius_max_pixels=14,
                    get_fill_color=[220, 38, 38, 235],
                    get_line_color=[255, 255, 255, 255],
                    line_width_min_pixels=2,
                    pickable=False,
                )
            )
        if not map_data.empty:
            map_layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data,
                    get_position="[longitude, latitude]",
                    get_radius=300,
                    radius_min_pixels=3,
                    radius_max_pixels=10,
                    get_fill_color="marker_color",
                    get_line_color="[255, 255, 255, 230]",
                    line_width_min_pixels=1,
                    pickable=True,
                    auto_highlight=True,
                    id="nearby_listings",
                )
            )

        with st.container(key="nearby_map_layer_switcher"):
            selected_map_style = st.selectbox(
                "Map layer",
                options=list(MAP_STYLES),
                key="nearby_map_layer_style",
                label_visibility="collapsed",
            )
        deck = pdk.Deck(
            map_style=MAP_STYLES[selected_map_style],
            initial_view_state=initial_view_state,
            layers=map_layers,
            tooltip={
                "html": map_tooltip_html(social_columns),
                "style": {
                    "backgroundColor": "transparent",
                    "color": "#0f172a",
                    "padding": "0",
                    "pointerEvents": "none",
                },
            },
        )
        chart_generation_key = f"nearby_map_chart_generation_{directory_key}"
        chart_generation = st.session_state.get(chart_generation_key, 0)
        chart_key = f"nearby_map_chart_{directory_key}_{chart_generation}"
        chart_state = st.pydeck_chart(
            deck,
            height=900 if zoom_map else 520,
            width="stretch",
            key=chart_key,
            on_select="rerun",
            selection_mode="single-object",
        )
        selected_objects = chart_state.selection.get("objects", {}).get(
            "nearby_listings", []
        )
        if selected_objects:
            selected_index = int(selected_objects[0]["listing_index"])
            listing = mapped.loc[selected_index].drop(
                labels=["_latitude", "_longitude"], errors="ignore"
            )
            st.session_state["detail_workbook"] = str(selected_workbook)
            st.session_state["detail_profile"] = listing.to_dict()
            st.session_state[chart_generation_key] = chart_generation + 1
            st.switch_page("pages/listing_detail.py")
        missing_coordinates = len(filtered) - len(mapped)
        if missing_coordinates:
            st.caption(
                f"{missing_coordinates:,} matching listings are not mapped because "
                "their coordinates are missing, invalid, or outside Nepal."
            )
