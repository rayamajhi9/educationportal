from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st


DATA_DIR = Path(__file__).resolve().parent
MISSING = "N/A"


@st.cache_data(show_spinner=False)
def get_sheet_names(workbook_path: str) -> list[str]:
    return pd.ExcelFile(workbook_path, engine="openpyxl").sheet_names


@st.cache_data(show_spinner="Reading workbook...")
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


def available_values(series: pd.Series, split_commas: bool = False) -> list[str]:
    values = set()
    for value in series:
        if value == MISSING:
            continue
        parts = value.split(",") if split_commas else [value]
        values.update(part.strip() for part in parts if part.strip() and part.strip() != MISSING)
    return sorted(values, key=str.casefold)


def token_match(series: pd.Series, selected: list[str]) -> pd.Series:
    selected_values = {value.casefold() for value in selected}
    if not selected_values:
        return pd.Series(False, index=series.index)
    return series.map(
        lambda value: bool(
            selected_values.intersection(
                token.strip().casefold() for token in str(value).split(",")
            )
        )
    )


def text_match(series: pd.Series, selected: list[str]) -> pd.Series:
    selected_values = [value.casefold() for value in selected]
    if not selected_values:
        return pd.Series(False, index=series.index)
    return series.map(
        lambda value: any(option in str(value).casefold() for option in selected_values)
    )


def make_initials(name: str) -> str:
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper() or "C"


def safe_logo_markup(url: str, name: str) -> str:
    parsed_url = urlsplit(url)
    if url != MISSING and parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
        return (
            f'<img class="listing-logo" src="{escape(url, quote=True)}" '
            f'alt="{escape(name, quote=True)} logo" loading="lazy" '
            'referrerpolicy="no-referrer">'
        )
    return f'<div class="listing-logo-fallback">{escape(make_initials(name))}</div>'


def reset_page() -> None:
    st.session_state["directory_page"] = 1


st.set_page_config(page_title="College/School Directory", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f5f7fa; }
    [data-testid="stAppViewContainer"] > .main { padding-top: 1.6rem; }
    h1 { color: #075985; font-family: Georgia, serif; font-size: 2rem !important; }
    .directory-subtitle { color: #64748b; margin: -.35rem 0 1.3rem; }
    .filter-title {
        color: #475569; font-size: 1rem; font-weight: 700;
        letter-spacing: .04em; margin-bottom: .9rem;
    }
    .filter-section {
        border-bottom: 1px solid #e2e8f0; color: #075985;
        font-size: .82rem; font-weight: 700; letter-spacing: .06em;
        margin: .4rem 0 .45rem; padding-bottom: .25rem; text-transform: uppercase;
    }
    .listing-card {
        align-items: flex-start; background: #fff; border: 1px solid #e2e8f0;
        border-radius: 8px; box-shadow: 0 2px 6px rgba(15, 23, 42, .07);
        display: flex; gap: 1.2rem; margin: 0 0 .9rem; min-height: 130px;
        padding: 1.2rem;
    }
    .listing-logo, .listing-logo-fallback {
        align-items: center; background: #f8fafc; border-radius: 6px;
        display: flex; flex: 0 0 82px; height: 82px; justify-content: center;
        object-fit: contain; padding: 4px; width: 82px;
    }
    .listing-logo-fallback { color: #075985; font-size: 1.4rem; font-weight: 700; }
    .listing-details { min-width: 0; }
    .listing-heading {
        align-items: baseline; color: #292f36; display: flex; flex-wrap: wrap;
        font-family: Georgia, serif; font-size: 1.35rem; font-weight: 700;
        gap: .2rem .55rem; line-height: 1.35; margin-bottom: .28rem;
    }
    .listing-city { color: #64748b; font-family: sans-serif; font-size: .95rem; font-weight: 500; }
    .listing-location, .listing-email { color: #475569; font-size: .95rem; margin-top: .22rem; }
    .listing-email a { color: #075985; text-decoration: none; }
    .listing-email a:hover { text-decoration: underline; }
    .listing-meta { color: #64748b; font-size: .83rem; margin-top: .55rem; }
    .result-count { color: #475569; font-size: .92rem; margin: .1rem 0 .8rem; }
    div[data-testid="stButton"] button { border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

workbooks = sorted(
    path for path in DATA_DIR.glob("collegenp_*_and_courses.xlsx")
    if not path.name.startswith("~$")
)
if not workbooks:
    st.warning(f"No CollegeNP workbooks found in {DATA_DIR}.")
    st.stop()

dataset_labels = {
    path: (
        "Colleges" if "colleges" in path.stem
        else "Schools" if "schools" in path.stem
        else path.stem
    )
    for path in workbooks
}
selected_workbook = st.selectbox(
    "Directory",
    workbooks,
    format_func=lambda path: dataset_labels[path],
    key="selected_directory",
    on_change=reset_page,
)
entity_sheet = next(
    sheet for sheet in get_sheet_names(str(selected_workbook)) if sheet != "Courses"
)
directory = load_sheet(str(selected_workbook), entity_sheet)
courses = load_sheet(str(selected_workbook), "Courses")
entity_name_column = next(
    (column for column in directory.columns if column.lower().endswith("name")),
    directory.columns[0],
)
course_entity_column = courses.columns[0]
name_column = entity_name_column
entity_singular = "college" if entity_sheet == "Colleges" else "school"
#st.title(f"List of {entity_sheet} in Nepal")
st.markdown(
    f'<div class="directory-subtitle">Browse {entity_singular} profiles from across Nepal.</div>',
    unsafe_allow_html=True,
)
st.page_link("pages/nearby_map.py", label="Explore listings on the map")

left_column, right_column = st.columns([0.27, 0.73], gap="large")

with left_column:
    with st.container(border=True):
        st.markdown('<div class="filter-title">☷ FILTER</div>', unsafe_allow_html=True)
        directory_key = selected_workbook.stem
        city_column = "City / District"
        stream_column = "Stream / Category"
        affiliation_column = "Affiliated By"
        type_column = next(
            (column for column in directory.columns if column.lower().endswith("type")),
            "College Type",
        )

        st.markdown('<div class="filter-section">⌖ City / District</div>', unsafe_allow_html=True)
        selected_cities = st.multiselect(
            "City / District",
            available_values(directory[city_column]),
            key=f"city_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        stream_values = set(available_values(directory[stream_column], split_commas=True))
        course_stream_column = "Stream / Specialization"
        stream_values.update(available_values(courses[course_stream_column], split_commas=True))
        st.markdown('<div class="filter-section">▤ Main stream</div>', unsafe_allow_html=True)
        selected_streams = st.multiselect(
            "Main stream",
            sorted(stream_values, key=str.casefold),
            key=f"stream_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        affiliation_values = set(available_values(directory[affiliation_column]))
        course_affiliation_column = "Affiliation Body for the specific course"
        affiliation_values.update(available_values(courses[course_affiliation_column]))
        st.markdown('<div class="filter-section">✓ Affiliated by</div>', unsafe_allow_html=True)
        selected_affiliations = st.multiselect(
            "Affiliated by",
            sorted(affiliation_values, key=str.casefold),
            key=f"affiliation_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        st.markdown('<div class="filter-section">▤ Course type</div>', unsafe_allow_html=True)
        selected_course_types = st.multiselect(
            "Course type",
            available_values(courses["Course Type"]),
            key=f"course_type_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        fee_columns = [
            column for column in ("Total Fee (with currency/amount)", "Total Fee")
            if column in courses
        ]
        fee_values = sorted(
            {
                value
                for column in fee_columns
                for value in available_values(courses[column])
            },
            key=str.casefold,
        )
        st.markdown('<div class="filter-section">₹ Course fee</div>', unsafe_allow_html=True)
        if fee_values:
            selected_fees = st.multiselect(
                "Course fee",
                fee_values,
                key=f"fee_{directory_key}",
                label_visibility="collapsed",
                on_change=reset_page,
            )
        else:
            selected_fees = []
            st.caption("Course fee data is not available in this workbook.")

        st.markdown('<div class="filter-section">▥ Type of college</div>', unsafe_allow_html=True)
        selected_types = st.multiselect(
            "Type of college",
            available_values(directory[type_column]),
            key=f"college_type_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        st.markdown('<div class="filter-section">▦ Duration</div>', unsafe_allow_html=True)
        selected_durations = st.multiselect(
            "Duration",
            available_values(courses["Duration"]),
            key=f"duration_{directory_key}",
            label_visibility="collapsed",
            on_change=reset_page,
        )

        page_size = st.selectbox(
            "Listings per page",
            [10, 20, 50],
            index=0,
            key=f"page_size_{directory_key}",
            on_change=reset_page,
        )

with right_column:
    search_text = st.text_input(
        "Search colleges",
        placeholder="Search by name, city, address, or email",
        key=f"search_{directory_key}",
        on_change=reset_page,
    )

    profile_mask = pd.Series(True, index=directory.index)
    if selected_cities:
        profile_mask &= directory[city_column].isin(selected_cities)
    if selected_types:
        profile_mask &= directory[type_column].isin(selected_types)
    if search_text.strip():
        searchable_columns = [
            column for column in (
                name_column,
                city_column,
                "Address (Full location detail)",
                "Contact Email",
            )
            if column in directory.columns
        ]
        search_mask = directory[searchable_columns].apply(
            lambda column: column.str.contains(
                search_text.strip(), case=False, regex=False, na=False
            )
        ).any(axis=1)
        profile_mask &= search_mask

    course_mask = pd.Series(True, index=courses.index)
    if selected_course_types:
        course_mask &= courses["Course Type"].isin(selected_course_types)
    if selected_durations:
        course_mask &= courses["Duration"].isin(selected_durations)
    if selected_fees:
        fee_match = pd.Series(False, index=courses.index)
        for column in fee_columns:
            fee_match |= courses[column].isin(selected_fees)
        course_mask &= fee_match

    eligible_course_names = set(courses.loc[course_mask, course_entity_column])
    if selected_course_types or selected_durations or selected_fees:
        profile_mask &= directory[name_column].isin(eligible_course_names)

    if selected_streams:
        profile_stream_match = token_match(directory[stream_column], selected_streams)
        course_stream_match = token_match(courses[course_stream_column], selected_streams)
        stream_course_names = set(
            courses.loc[course_mask & course_stream_match, course_entity_column]
        )
        profile_mask &= profile_stream_match | directory[name_column].isin(stream_course_names)

    if selected_affiliations:
        profile_affiliation_match = text_match(
            directory[affiliation_column], selected_affiliations
        )
        course_affiliation_match = text_match(
            courses[course_affiliation_column], selected_affiliations
        )
        affiliation_course_names = set(
            courses.loc[course_mask & course_affiliation_match, course_entity_column]
        )
        profile_mask &= (
            profile_affiliation_match
            | directory[name_column].isin(affiliation_course_names)
        )

    filtered = directory.loc[profile_mask].drop_duplicates().reset_index(drop=True)
    total_rows = len(filtered)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    st.session_state["directory_page"] = min(
        max(1, st.session_state.get("directory_page", 1)),
        total_pages,
    )
    current_page = st.session_state["directory_page"]
    start_index = (current_page - 1) * page_size
    page_rows = filtered.iloc[start_index : start_index + page_size]

    first_result = start_index + 1 if total_rows else 0
    last_result = min(start_index + page_size, total_rows)
    st.markdown(
        f'<div class="result-count">Showing <b>{first_result:,}–{last_result:,}</b> '
        f'of <b>{total_rows:,}</b> listings</div>',
        unsafe_allow_html=True,
    )

    for row_offset, (_, listing) in enumerate(page_rows.iterrows()):
        name = str(listing.get(name_column, MISSING))
        city = str(listing.get(city_column, MISSING))
        address = str(listing.get("Address (Full location detail)", MISSING))
        email = str(listing.get("Contact Email", MISSING))
        logo = str(listing.get("College Logo URL", listing.get("School Logo URL", MISSING)))
        listing_type = str(listing.get(type_column, MISSING))
        stream = str(listing.get(stream_column, MISSING))
        location = address if address != MISSING else city
        email_markup = (
            f'<a href="mailto:{escape(email, quote=True)}">{escape(email)}</a>'
            if email != MISSING
            else "Email not listed"
        )
        metadata = " · ".join(
            value for value in (listing_type, stream) if value != MISSING
        )
        st.markdown(
            f'<article class="listing-card">'
            f'{safe_logo_markup(logo, name)}'
            f'<div class="listing-details">'
            f'<div class="listing-heading">{escape(name)}'
            f'<span class="listing-city">{escape(city)}</span></div>'
            f'<div class="listing-location">📍 {escape(location)}</div>'
            f'<div class="listing-email">✉ {email_markup}</div>'
            f'<div class="listing-meta">{escape(metadata)}</div>'
            f'</div></article>',
            unsafe_allow_html=True,
        )
        action_spacer, action_column = st.columns([5, 1])
        with action_column:
            if st.button(
                "View details",
                key=f"detail_{directory_key}_{start_index + row_offset}",
                width="stretch",
            ):
                st.session_state["detail_workbook"] = str(selected_workbook)
                st.session_state["detail_profile"] = listing.to_dict()
                st.switch_page("pages/listing_detail.py")

    if not total_rows:
        st.info("No listings match these filters. Try removing a filter or changing your search.")

    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        page_numbers = sorted(
            set(
                [
                    1,
                    total_pages,
                    *range(
                        max(1, current_page - 1),
                        min(total_pages, current_page + 1) + 1,
                    ),
                ]
            )
        )
        pages_to_show: list[int | None] = []
        for index, number in enumerate(page_numbers):
            if index and number - page_numbers[index - 1] > 1:
                pages_to_show.append(None)
            pages_to_show.append(number)

        controls: list[tuple[str, int | None]] = [
            ("‹", max(1, current_page - 1)),
            *[
                (str(number) if number is not None else "…", number)
                for number in pages_to_show
            ],
            ("›", min(total_pages, current_page + 1)),
        ]
        columns = st.columns(len(controls))
        for column, (label, target_page) in zip(columns, controls):
            with column:
                if target_page is None:
                    st.caption(label)
                elif st.button(
                    label,
                    key=f"page_{directory_key}_{label}_{target_page}",
                    type="primary" if target_page == current_page and label.isdigit() else "secondary",
                    disabled=target_page == current_page,
                    width="stretch",
                ):
                    st.session_state["directory_page"] = target_page
                    st.rerun()

    if total_rows:
        st.download_button(
            "Download filtered listings as CSV",
            data=filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{selected_workbook.stem}_filtered.csv",
            mime="text/csv",
        )
