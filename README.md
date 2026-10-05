# educationportal

## Run the CollegeNP directory

Install the app dependencies and start Streamlit:

```sh
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Keep the CollegeNP `.xlsx` workbooks in the project root. The directory reads
both college and school listings from those workbooks. Select **View details**
on any listing to open its full profile and all associated course information.
Use **Explore listings on the map** to browse matching listings with valid Nepal
coordinates on an interactive map. Its Filters dialog includes city/district,
main stream, affiliation, course type, course fee, institution type, and duration.
The nearby map overlays all 77 Nepal district boundaries and highlights matching
districts when selected. The boundary data is simplified for display and sourced
from [MOFAGA-derived Nepal GeoJSON](https://github.com/Parajulibkrm/new-nepal-geojson-and-topojson/tree/1ce78760e8b15aa59f7124852491040d7294228b/Geojson);
the map automatically fits to matching listings and selected district boundaries.