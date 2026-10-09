# CollegeNP Directory — Product and Design Specification Prompt

## Role

Act as a senior product designer and Streamlit engineer. Build and maintain a
polished, responsive directory for Nepalese colleges and schools using the
provided CollegeNP spreadsheet data. Follow the existing repository patterns,
preserve current functionality, and make complete, verifiable changes.

## Product goal

Create one application where people can:

1. Browse college or school listings with useful filters and pagination.
2. Open a complete profile and see all related course information.
3. Explore filtered listings on an interactive map using an Airbnb-inspired
   nearby-search and filter-dialog interaction.

Use Airbnb only as interaction and visual-layout inspiration. Do not copy its
branding, assets, wording, or proprietary implementation.

## Data sources and workbook handling

- Read the Excel workbooks in the project root matching
  `collegenp_*_and_courses.xlsx`.
- Support both available datasets:
  - `collegenp_colleges_and_courses.xlsx`, with `Colleges` and `Courses` sheets.
  - `collegenp_schools_and_courses.xlsx`, with `Schools` and `Courses` sheets.
- Let the user switch between Colleges and Schools. Keep the selected dataset
  consistent as users move between directory, detail, and map views.
- Load spreadsheet fields as text, trim whitespace, represent missing values as
  `N/A`, and avoid duplicate listings in displayed results.
- Use the first course-sheet column as the institution key; match courses to
  profiles by the corresponding college or school name.
- Preserve the workbook's column names and show all profile/course fields on a
  detail page. Do not assume course fees or map coordinates always exist.
- Course fee fields are present in the schema, but the current workbooks have no
  populated fee values. Keep the fee filter visible and explain when data is
  unavailable; never invent fee values.
- The nearby map uses bundled, simplified district polygon data for all 77 Nepal
  districts in `assets/nepal_districts.geojson`. Preserve this asset when updating
  map behavior. Its source is the
  [MOFAGA-derived Nepal GeoJSON dataset](https://github.com/Parajulibkrm/new-nepal-geojson-and-topojson/tree/1ce78760e8b15aa59f7124852491040d7294228b/Geojson).

### Institution sheet schema

The Colleges and Schools sheets share these columns (logo column varies by
dataset):

1. College Name / School Name
2. City / District
3. Address (Full location detail)
4. College Type / School Type
5. Affiliated By
6. Number of Affiliations
7. Number of Courses Offered
8. Stream / Category
9. Infrastructure & Facilities
10. Review Rating
11. Total Number of Reviews
12. Contact Phone Numbers
13. Contact Email
14. Official Website URL
15. Map Latitude
16. Map Longitude
17. Established year
18. College Logo URL / School Logo URL

### Courses sheet schema

1. College Name / School Name (institution link key)
2. Course Name
3. Course Type
4. Stream / Specialization
5. Duration
6. Total Fee (with currency/amount)
7. Affiliation Body for the specific course
8. Total Fee
9. Study Mode
10. Total seats
11. Medium
12. Recognition
13. Overview
14. FAQ

## Application design

### Shared visual direction

- Use a clean education-directory interface with a restrained palette, readable
  typography, generous spacing, clear hierarchy, and consistent components.
- Prefer a light neutral background, white cards, subtle borders/shadows, and
  dark-blue/teal accents already used by the application.
- Make layouts usable on both desktop and narrow screens. Do not make essential
  content or actions desktop-only.
- Provide clear empty, loading, and missing-data states.
- Escape untrusted text before rendering HTML. Validate external URLs before
  using them for logos, websites, or links.

### Directory page

- Provide a dataset selector for Colleges and Schools.
- Present filters in a clear left-side panel and matching listing cards on the
  right on wide screens; adapt cleanly on smaller screens.
- Include filters for:
  - City / District
  - Main stream (combine profile streams and course specializations)
  - Affiliated by (profile and course affiliations)
  - Course type
  - Course fee
  - Institution type
  - Duration
- Include free-text search by institution name, city, address, and contact email.
- Each listing card should show its logo when valid, institution name, location,
  contact email when available, and useful type/stream metadata.
- Include a **View details** action for each listing.
- Paginate results, reset to the first page when filters/search/dataset changes,
  show the result count, and provide a filtered-list CSV download.
- If a course-based filter is selected, only include institutions with matching
  courses. Combine multiple active filters predictably.

### Institution detail page

- Show the institution name, logo, city/address, and available contact actions
  (email, phone, official website).
- Adapt the detail header, contact actions, profile fields, and course information
  to narrow screens. Stack columns as needed and prevent long values from causing
  horizontal page scrolling.
- Show every field from that institution's workbook row, not only a curated
  subset. Render missing values as `N/A`.
- Show all courses associated with the institution. Include every course-sheet
  field; make long Overview and FAQ content readable and expand/collapse course
  details as appropriate.
- If valid coordinates are available, provide a Google Maps location link.
- Provide a download of the selected profile and its related courses.
- Include navigation back to the directory and to the nearby map.

### Nearby map page

- Keep the listing search and map together in a clear split layout. Show matching
  listings alongside an interactive map; allow map controls such as zoom and
  fullscreen.
- Adapt the nearby results/map layout to tablet and mobile widths. Stack the map
  and results on narrow screens, keep map controls and the location action usable,
  and avoid horizontal overflow. Keep map-only mode and its filter drawer usable
  at mobile viewport sizes.
- On desktop, keep the nearby page title/search/filter controls sticky while
  scrolling, make the left results list independently scrollable with its heading
  and result count kept in view, and keep the map panel sticky below the controls
  alongside the list.
  On narrow screens, allow a natural stacked layout without trapping the map in
  a sticky panel.
- Render all 77 district boundaries as a lightweight GeoJSON polygon layer and
  highlight selected districts when the City / District filter matches them.
  Normalize district names and support workbook aliases, including split/current
  administrative names such as Nawalpur/Parasi and Rukum.
- Plot listings only when latitude/longitude are numeric, within valid geographic
  ranges, and geographically within Nepal's boundary extent. Do not drop a listing
  from results because coordinates are missing, invalid, or outside Nepal; explain
  how many matching listings are not mapped.
- Automatically fit the initial map view to selected district polygons when
  districts are selected; otherwise fit to valid matching listing coordinates.
  Provide a useful Nepal-wide starting view when neither exists, and a reasonable
  zoom for a single point.
- Offer a **Your location** control that explicitly requests browser geolocation
  permission, centers the map on the returned coordinates, and shows a distinct
  user-location marker. Do not request or store location until the user activates
  the control; report denied, unavailable, unsupported, and timeout cases clearly.
- Map hover details should show the institution logo, name, location, email, website,
  and available social links. If the user clicks the corresponding map pin, open
  that institution's detail page.
- Color listing pins by the institution's College Type / School Type and display
  a matching map legend. Use a clearly distinct legend entry for the user's GPS
  location marker when one has been requested.
- Listing cards should show logo when valid, name, district/address, and
  institution type, with a **View details** action.
- Paginate map-page listing results and reset pagination when filters, search,
  or dataset changes.
- Include free-text search by institution name, city, and address.

#### Map-only results and filter sidebar

- Use Google Maps' split results/map layout as the interaction reference. Keep the
  existing Streamlit and PyDeck stack; do not add a mapping dependency.
- Keep the regular nearby page focused on search and results; do not show the
  map-only filter controls there. Provide a **Zoom map** action that
  switches into a map-only, viewport-filling mode with an **Exit map** action.
- In map-only mode, show a collapsible left sidebar beside the map. Its results
  view includes listing search, the applied-filter summary, matching listing cards,
  and pagination. Keep the results independently scrollable so all results and
  controls remain reachable. On narrow screens, show the sidebar as an overlay
  drawer without horizontal overflow.
- Show an **All filters** control on the map with the active filter-group count.
  Selecting it switches the left sidebar from results to the filter view instead
  of opening another panel over the map. Provide a back-arrow action to return to
  results without applying draft changes.
- In the filter view, keep a header with back, **Clear**, and **Done** actions,
  grouped sections, and a scrollable filter body. **Clear** clears draft choices;
  **Done** applies them and returns to results.
- Provide the same seven filter fields in the panel, in this order:
  1. City / District
  2. Main stream
  3. Affiliated by
  4. Course type
  5. Course fee
  6. Type of college / school
  7. Duration
- Use multi-select controls with a clear “Choose options” empty state. Keep
  selected options visible and editable.
- Stage filter edits until **Done** is selected. Applying an empty draft resets all
  applied filters. Returning to results or collapsing the sidebar must not apply
  uncommitted changes; preserve draft selections when reopening, applied filters,
  and the active-filter count.
- Keep the map controls, location action, and **Exit map** available when the
  sidebar is collapsed. Place the results-sidebar collapse/restore control on the
  sidebar's vertical map-facing edge, centered vertically, rather than in the
  top toolbar or results list.
- In map-only mode, place the map-layer selector, zoom controls, and **Your
  location** control together at the bottom-right of the map. Offer light, street,
  and dark basemap styles.
- Show a compact summary of applied filters and update the filter count.
- The Course fee control must remain visible but disabled with a plain-language
  note when the selected workbook has no fee data.

## Filtering behavior

- Multiple values within one multi-select are alternatives; different active
  filter groups combine as an intersection.
- City and institution type match institution profile fields.
- Main stream can match either `Stream / Category` or a related course's
  `Stream / Specialization`.
- Affiliation can match either institution `Affiliated By` or a related course's
  `Affiliation Body for the specific course`.
- Course type, duration, and fee match course rows and then include only
  institutions linked to at least one matching course.
- When several course filters are selected, they must match the same course row,
  rather than separate unrelated courses for the same institution.
- When a workbook lacks a field, show a safe unavailable state and do not crash.

## Technical expectations

- Continue using Streamlit, pandas, openpyxl, and PyDeck already present in the
  project unless there is a concrete need to change the stack.
- Reuse existing sheet-loading and filtering patterns where appropriate.
- Keep data processing, page state, and presentation understandable and
  type-safe. Avoid silent error swallowing and speculative fallback values.
- Do not add dependencies unless required; if a dependency is added, update the
  existing requirements file and explain why.
- Keep navigation paths consistent with Streamlit multipage routing and preserve
  the dataset/profile state needed by detail views.
- Update documentation when the user-facing workflow changes.
- Do not create additional planning files unless explicitly requested.

## Definition of done

- Both college and school workbooks render correctly.
- Directory, detail, and map pages remain connected and dataset-aware.
- All seven requested map filters are present, have clear unavailable states,
  and apply/reset correctly.
- Search, course-aware filters, the collapsible map results/filter sidebar, pagination,
  district overlays, map auto-fit, valid map pins, and detail links work.
- Missing, invalid, or out-of-Nepal coordinates do not remove listings from
  results; missing fee values are not fabricated.
- Validate changes with the narrowest relevant checks available (syntax/type
  diagnostics and an app/browser smoke test where feasible).
- Report what changed, what was verified, and any remaining data limitations.
