from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st


DATA_DIR = Path(__file__).resolve().parents[1]
MISSING = "N/A"

st.set_page_config(page_title="Listing details | CollegeNP", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f5f7fa; }
    [data-testid="stAppViewContainer"] > .main { padding-top: 1.6rem; }
    h1, h2, h3 { color: #075985; font-family: Georgia, serif; }
    .detail-subtitle { color: #64748b; margin-top: -.6rem; }
    .detail-logo {
        align-items: center; background: #fff; border: 1px solid #e2e8f0;
        border-radius: 10px; display: flex; justify-content: center;
        max-height: 180px; max-width: 180px; object-fit: contain; padding: 8px;
    }
    .field-label {
        color: #64748b; font-size: .78rem; font-weight: 700;
        letter-spacing: .04em; margin-bottom: .15rem; text-transform: uppercase;
    }
    .field-value { color: #1e293b; overflow-wrap: anywhere; }
    .detail-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, .05); margin-bottom: .8rem;
        padding: 1rem 1.1rem;
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


def show_field(label: str, value: str) -> None:
    st.markdown(
        f'<div class="field-label">{escape(label)}</div>'
        f'<div class="field-value">{escape(value).replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )


def is_safe_web_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


workbook_path = st.session_state.get("detail_workbook")
profile_data = st.session_state.get("detail_profile")
if not workbook_path or not profile_data or not Path(workbook_path).is_file():
    st.info("Choose a listing from the directory to view its details.")
    st.page_link("streamlit_app.py", label="← Back to directory")
    st.stop()

workbook_name = Path(workbook_path).name
entity_sheet = next(
    sheet
    for sheet in pd.ExcelFile(workbook_path, engine="openpyxl").sheet_names
    if sheet != "Courses"
)
profile = pd.Series(profile_data)
name_column = next(
    (column for column in profile.index if column.lower().endswith("name")),
    profile.index[0],
)
entity_name = str(profile.get(name_column, MISSING))
courses = load_sheet(workbook_path, "Courses")
course_name_column = courses.columns[0]
related_courses = courses.loc[courses[course_name_column] == entity_name]

st.page_link("streamlit_app.py", label="← Back to directory")

logo_column = next(
    (column for column in profile.index if column.lower().endswith("logo url")),
    None,
)
logo_url = str(profile.get(logo_column, MISSING)) if logo_column else MISSING
header_columns = st.columns([1, 5], vertical_alignment="center")
with header_columns[0]:
    if is_safe_web_url(logo_url):
        st.markdown(
            f'<img class="detail-logo" src="{escape(logo_url, quote=True)}" '
            f'alt="{escape(entity_name, quote=True)} logo" loading="lazy" '
            'referrerpolicy="no-referrer">',
            unsafe_allow_html=True,
        )
with header_columns[1]:
    st.title(entity_name)
    city = str(profile.get("City / District", MISSING))
    address = str(profile.get("Address (Full location detail)", MISSING))
    st.markdown(
        f'<div class="detail-subtitle">{escape(city)}'
        f'{" · " + escape(address) if address != MISSING else ""}</div>',
        unsafe_allow_html=True,
    )

contact_columns = st.columns(3)
email = str(profile.get("Contact Email", MISSING))
website = str(profile.get("Official Website URL", MISSING))
phone = str(profile.get("Contact Phone Numbers", MISSING))
if email != MISSING:
    contact_columns[0].link_button("Email", f"mailto:{email}", width="stretch")
if is_safe_web_url(website):
    contact_columns[1].link_button("Official website", website, width="stretch")
if phone != MISSING:
    contact_columns[2].markdown(f"**Phone**  \n{escape(phone)}")

st.subheader("Profile information")
st.caption(f"All {len(profile)} fields from the {entity_sheet} sheet")

fields = list(profile.items())
for start in range(0, len(fields), 2):
    columns = st.columns(2)
    for column, (label, raw_value) in zip(columns, fields[start : start + 2]):
        value = str(raw_value)
        with column:
            with st.container(border=True):
                show_field(str(label), value)

latitude = str(profile.get("Map Latitude", MISSING))
longitude = str(profile.get("Map Longitude", MISSING))
if latitude != MISSING and longitude != MISSING:
    st.link_button(
        "Open location in Google Maps",
        f"https://www.google.com/maps?q={escape(latitude, quote=True)},{escape(longitude, quote=True)}",
    )

st.subheader(f"Courses offered ({len(related_courses):,})")
st.caption(f"All {len(courses.columns)} fields from the Courses sheet are shown for each course.")

if related_courses.empty:
    st.info("No course records are linked to this listing.")
else:
    long_text_fields = {"Overview", "FAQ"}
    for course_index, (_, course) in enumerate(related_courses.iterrows(), start=1):
        course_name = str(course.get("Course Name", f"Course {course_index}"))
        with st.expander(f"{course_index}. {course_name}"):
            course_fields = list(course.items())
            regular_fields = [
                (label, value)
                for label, value in course_fields
                if label not in long_text_fields
            ]
            for start in range(0, len(regular_fields), 2):
                columns = st.columns(2)
                for column, (label, raw_value) in zip(
                    columns, regular_fields[start : start + 2]
                ):
                    with column:
                        with st.container(border=True):
                            show_field(str(label), str(raw_value))

            for label, raw_value in course_fields:
                if label in long_text_fields:
                    st.markdown(f"#### {label}")
                    value = str(raw_value)
                    st.write(value if value != MISSING else MISSING)

st.download_button(
    "Download this listing and its courses as CSV",
    data=pd.concat(
        [
            profile.to_frame().T.assign(**{"Record Type": "Listing"}),
            related_courses.assign(**{"Record Type": "Course"}),
        ],
        ignore_index=True,
    ).to_csv(index=False).encode("utf-8-sig"),
    file_name=f"{entity_name.replace('/', '-')}_details.csv",
    mime="text/csv",
)
