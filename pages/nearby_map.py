import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_DIR = Path(__file__).resolve().parents[1]
DISTRICT_BOUNDARIES_PATH = DATA_DIR / "assets" / "nepal_districts.geojson"
MISSING = "N/A"
PAGE_SIZE = 8
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
    [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
        position: sticky; top: 11rem; z-index: 4;
    }
    [data-testid="stDialog"] > div {
        max-height: calc(100vh - 3rem); overflow-y: auto;
    }
    [data-testid="stDialog"] .st-key-nearby_filter_dialog_footer {
        background: #fff; border-top: 1px solid #e2e8f0;
        bottom: 0; padding: .75rem 0 .25rem; position: sticky; z-index: 2;
    }
    .filter-group-heading {
        border-bottom: 1px solid #e2e8f0; color: #0f172a;
        font-size: 1.05rem; font-weight: 700;
        margin: .7rem 0 .9rem; padding-bottom: .5rem;
    }
    @media (max-width: 900px) {
        .st-key-nearby_results_scroll {
            height: auto; max-height: 70vh; min-height: 0;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_map_panel) {
            position: static;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-nearby_sticky_header) {
            top: 0;
        }
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
    for state_key in keys.values():
        st.session_state[f"{state_key}_draft"] = list(
            st.session_state.get(state_key, [])
        )
    st.session_state["nearby_filter_dialog_open"] = True


def clear_draft_filters(keys: dict[str, str]) -> None:
    for state_key in keys.values():
        st.session_state[f"{state_key}_draft"] = []


def close_filter_dialog() -> None:
    st.session_state["nearby_filter_dialog_open"] = False


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
with st.container(key="nearby_sticky_header"):
    st.title(f"Find {entity_sheet.lower()} nearby")
    filter_bar, search_bar = st.columns(
        [0.35, 0.65], vertical_alignment="center"
    )
    with filter_bar:
        st.button(
            f"☷  Filters{f' · {selected_filter_count}' if selected_filter_count else ''}",
            key=f"open_nearby_filters_{directory_key}",
            on_click=begin_filter_edit,
            args=(filter_keys,),
            type="secondary",
        )
    with search_bar:
        search_text = st.text_input(
            "Search",
            placeholder="Search by name, city, or address",
            key=f"nearby_search_{directory_key}",
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


@st.dialog("Filters", width="large", on_dismiss=close_filter_dialog)
def show_filter_dialog() -> None:
    st.caption("Choose any combination of filters to refine your search.")
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

    with st.container(key="nearby_filter_dialog_footer"):
        clear_column, apply_column = st.columns(
            [1, 1], vertical_alignment="center"
        )
        clear_column.button(
            "Clear all",
            key=f"clear_nearby_filters_{directory_key}",
            on_click=clear_draft_filters,
            args=(filter_keys,),
        )
        if apply_column.button(
            "Show results",
            key=f"apply_nearby_filters_{directory_key}",
            type="primary",
            width="stretch",
        ):
            for state_key in filter_keys.values():
                st.session_state[state_key] = list(
                    st.session_state.get(f"{state_key}_draft", [])
                )
            st.session_state["nearby_filter_dialog_open"] = False
            st.session_state["nearby_page"] = 1
            st.rerun(scope="app")


if st.session_state.get("nearby_filter_dialog_open", False):
    show_filter_dialog()

results_column, map_column = st.columns([0.46, 0.54], gap="medium")

with results_column:
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

    with st.container(key="nearby_results_scroll"):
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
                "←", disabled=page == 1, key=f"nearby_prev_{selected_workbook.stem}"
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
        st.subheader("Map")
        highlighted_districts = selected_district_features(
            district_boundaries, selected_cities
        )
        if mapped.empty:
            st.caption(
                "No matching listings have valid map coordinates. Add latitude "
                "and longitude values within Nepal to show map pins; district "
                "boundaries remain available for reference."
            )
        map_data = pd.DataFrame(
            {
                "name": mapped[name_column],
                "city": mapped[city_column]
                if city_column in mapped
                else MISSING,
                "address": mapped["Address (Full location detail)"]
                if "Address (Full location detail)" in mapped
                else MISSING,
                "longitude": mapped["_longitude"],
                "latitude": mapped["_latitude"],
            }
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
        if len(set(fit_positions)) > 1:
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
        if not map_data.empty:
            map_layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data,
                    get_position="[longitude, latitude]",
                    get_radius=650,
                    get_fill_color="[8, 145, 178, 210]",
                    get_line_color="[255, 255, 255, 230]",
                    line_width_min_pixels=1,
                    pickable=True,
                    auto_highlight=True,
                )
            )

        deck = pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=initial_view_state,
            layers=map_layers,
            tooltip={
                "html": "<b>{name}</b><br/>{city}<br/>{address}",
                "style": {
                    "backgroundColor": "#0f172a",
                    "color": "white",
                    "padding": "8px",
                },
            },
        )
        st.pydeck_chart(deck, height=520, width="stretch")
        missing_coordinates = len(filtered) - len(mapped)
        if missing_coordinates:
            st.caption(
                f"{missing_coordinates:,} matching listings are not mapped because "
                "their coordinates are missing, invalid, or outside Nepal."
            )
