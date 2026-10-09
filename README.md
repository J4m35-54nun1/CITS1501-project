# Australian Aboriginal and Torres Strait Islander population Explorer (CITS1501)

An interactive web application exploring Aboriginal and Torres Strait Islander population data across Australian States, Territories, and Local Government Areas (LGAs).

## Overview
The **Australian Aboriginal and Torres Strait Islander population Explorer** enables users to analyse demogrphic distributions, compute regional population metrics, compare state/territory statistical, and view interactive visualisations. The applicaiton uses 2021 Australian Bureau of Statistics (ABS) Census data.

## Dataset Information
* **Source:** Australian Bureau of Statistics (ABS) 2021 Census
* **Coverage:** Local Government Areas (LGAs) across 8 states and Territories
* **Licensing** Creative Commons Attribution 4.0 international (CC BY 4.0)

## Setup Instructions

1. Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```

## Data API

The census tables currently live as CSV files in `Data (Database)`. The central
Flask service loads and combines the LGA, IREG, IARE, GCCSA, and ILOC datasets
through their individual loaders, then serves normalized JSON records to the
frontend.

Run the map and service from the project root:

```powershell
python ".\Interface (Frontend)\Interface.py"
```

Open `http://127.0.0.1:5000` in a browser. Hover over a state or territory to
see its “Aboriginal and/or Torres Strait Islander” count, share of the total
population, and change since the previous Census. Select it to zoom to Local
Government Area (LGA) boundaries. The year selector updates the map. The chart
compares counts for 2011, 2016, and 2021; hover over or focus a bar to see its
share of the whole population.

Stop the service with **Ctrl+C in the same terminal that started it**. The
launcher does not use Flask's development reloader and closes its listening
socket when interrupted. If the service was started in another terminal, stop
it from that terminal; Ctrl+C in a different terminal cannot interrupt it.

The map uses official 2021 ABS State/Territory and LGA boundaries, converted to
GeoJSON at `Interface (Frontend)/assets/australia_boundaries_2021.json`. The
source archives are available from the
[ABS ASGS Edition 3 digital boundary files](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files)
page and are licensed under Creative Commons Attribution 4.0 International.
To rebuild the GeoJSON asset from the downloaded ABS ZIP files:

```powershell
python ".\Source (Backend)\build_map_boundaries.py" `
  --lga-zip ".\LGA_2021_AUST_GDA2020_SHP.zip" `
  --state-zip ".\STE_2021_AUST_SHP_GDA2020.zip"
```

The service listens on `http://127.0.0.1:5000`. Available API endpoints:

* `GET /api/health` — checks that the service is responding.
* `GET /api/states` — returns state/territory counts derived by summing their
  GCCSA subregions.
* `GET /api/metadata` — lists dataset types, census years, and total records.
* `GET /api/data` — returns records with optional `region_type`, `year`,
  `region_name`, `state`, `limit`, and `offset` query parameters. For example:
  `http://127.0.0.1:5000/api/data?region_type=lga&state=Queensland&year=2021`

The data endpoint defaults to 1,000 records per response and supports a maximum
page size of 10,000. A SQL database is not configured in this project; the CSV
files are the current data source. The included Census tables provide the
combined “Aboriginal and/or Torres Strait Islander” category, not separate
Aboriginal-only, Torres Strait Islander-only, and both counts; the map labels
and explains this rather than presenting fabricated values.
