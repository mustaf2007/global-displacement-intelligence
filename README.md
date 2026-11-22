# Global Refugee & Displacement Intelligence

An open-source Streamlit research dashboard for exploring official population statistics on refugees and other people affected by forced displacement and statelessness worldwide.

**Primary source:** [UNHCR Refugee Data Portal](https://refugeedata.unhcr.org/)  
**Series:** `PopStatsOfficial`  
**Stack:** Python, Pandas, Streamlit and Plotly.

## Current features

- On-demand retrieval of all available UNHCR population-statistics records from 1960 onward for the selected category, with pagination and a 24-hour cache.
- 24-hour application cache to reduce repeated API requests.
- Source schema validation and numeric parsing.
- Population-category, reporting-period and custom inclusive historical-range filters, including all periods returned from 1960 onward.
- Country-of-asylum/hosting and country-of-origin rankings.
- Historical country trends, reporting-period coverage and comparable-period change analysis.
- Global displacement trends, decade-level summaries that treat stock and flow measures separately, and multi-country historical comparisons, and country profiles across separately reported refugee, IDP, asylum-seeker and other population categories using explicit UNHCR total records only.
- Descriptive displacement-pressure signals with strict missing-data and comparability rules.
- Somalia hosting/origin profile and a subnational displacement data workspace.
- Somalia IOM DTM Emergency Trend Tracking (ETT) Week 19 snapshot, with origin and destination marginal distributions, regional map, CSV exports and reconciliation checks.
- Safeguards against creating global totals by summing overlapping records.

The platform is a research and monitoring prototype. It does not currently implement predictive machine learning or individual origin-to-destination route modelling.

## Public data access

The UNHCR API requires no account, API key or token.

- CSV: https://api-data.unhcr.org/api/v0/data/export/PopStatsOfficial
- Metadata: https://api-data.unhcr.org/api/v0/metadata/PopStatsOfficial
- Constraints: https://api-data.unhcr.org/api/v0/constraints/PopStatsOfficial
- [API documentation](https://refugeedata.unhcr.org/en/documentation/technical-reference/api/)
- [Official data series](https://refugeedata.unhcr.org/en/data-finder/detail/PopStatsOfficial/data/)

**API use limitation:** UNHCR describes the API as a best-effort service for analysis, research and occasional integration, not a guaranteed production backend for third-party products or frequent scheduled bulk extraction. For a public service or continuous/high-volume access, contact UNHCR to discuss requirements. The app caches the downloaded snapshot in memory and does not schedule frequent bulk downloads.

## Run locally

Python 3.10 or later:

```bash
git clone https://github.com/mustaf2007/global-displacement-intelligence.git
cd global-displacement-intelligence
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The first run retrieves the selected population category's available history from 1960 onward. An internet connection to `api-data.unhcr.org` is required; large categories may take longer because the API is paginated.

## Deploy

1. Open https://share.streamlit.io/.
2. Connect this GitHub repository.
3. Select branch `main` and entry point `app.py`.
4. Deploy. No secrets are required for the UNHCR dashboard. To enable the optional IOM DTM API explorer, add `DTMAPI_SUBSCRIPTION_KEY` under the app's Streamlit secrets; without it, the explorer remains safely disabled and the rest of the dashboard continues to work.

## Statistical safeguards

- Treat population counts as stocks. Do not sum across years.
- Do not add country-of-asylum and country-of-origin figures; they are different views and may overlap.
- Do not sum sex, age, urbanisation or setting breakdowns when total (`_T`) records are available.
- Missing values are not zero.
- Display a global total only when the source explicitly provides an unambiguous global aggregate.
- Country rankings use one reporting period and one geographic role at a time.

Inspect UNHCR metadata and constraints before extending the indicators.

## Project status

The dashboard includes UNHCR global population-statistics analysis and a separately sourced Somalia IOM DTM ETT research workspace. GitHub Actions runs automated checks on repository changes. A successful CI run verifies the checks in the workflow; it does not certify the completeness of external data, guarantee third-party API uptime, or independently validate every live map service. Verify source releases and coverage before using results in policy or research outputs.

## Somalia displacement data: interpretation and coverage

The Somalia subnational workspace presents IOM DTM Emergency Trend Tracking (ETT) information separately from UNHCR population stocks.

- The displayed Week 19 snapshot reports 10,451 new arrivals, 114,553 cumulative arrivals since June 2026 and 16 assessed districts.
- Origin and destination region counts are separate marginal distributions. They are not a person-level origin–destination matrix and cannot establish bilateral routes, net migration or regional gains/losses.
- The origin and destination distributions each sum arithmetically to the reported Week 19 headline. This is a consistency check, not proof that each record represents a unique person or one-to-one movement.
- ETT new arrivals are event-tracking flows and must not be interpreted as the total IDP population currently residing in Somalia. Secondary or repeated displacement may be included.
- Monitoring coverage is partial and changes over time. An unassessed district is not a zero-displacement district.
- ETT findings are estimates based on remote and in-person key-informant interviews, not a census or person-level registration. Many indicators describe the majority of displaced people at a location; detailed origins are not exhaustive.
- Coverage focuses on main urban centres and surrounding areas in assessed districts, not every settlement or the full district population. GPS coordinates may be approximate.
- Weekly comparisons must account for changing district coverage, collection pauses and interview-mode changes; missing weeks must not be interpolated as observed zeroes.
- Week 20 report availability is linked in the app, but its numerical figures are not displayed until extracted and verified.

Sources:
- [IOM DTM Somalia](https://dtm.iom.int/somalia)
- [IOM Somalia ETT dataset](https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0)
- [IOM Week 19 ETT report](https://dtm.iom.int/reports/somalia-emergency-trend-tracking-report-week-19-31-october-04-november-2026)
- [IOM Q2 2026 ETT overview and methodology](https://dtm.iom.int/sites/g/files/tmzbdl1461/files/reports/DTM_SOM_ETT_Q2_2026_2.pdf?iframe=true)

The current DTM dataset page is a source and coverage reference. Do not assume that a keyless, stable machine-readable API is available: the DTM API v3 requires a developer account/subscription key, and older API versions are no longer maintained.

## Attribution

Data source: UNHCR Refugee Data Portal. Retain attribution and comply with current terms of use and data-governance guidance.

## License

MIT License. See `LICENSE`.


### Explicit global totals and reporting status

The dashboard displays a global total only when a unique explicit total record is present in the source data for the selected population category and reporting period. It distinguishes totals that are reported, not reported, missing a usable value, or ambiguous because conflicting values exist. Country-level observations are never added together to manufacture a global total.


### Somalia integrated displacement profile

The Somalia profile presents UNHCR population-statistics series and IOM DTM Emergency Trend Tracking evidence in separate sections. The IOM Week 19 snapshot (31 October–4 November 2026) reports 10,451 new arrivals, 114,553 cumulative arrivals since 14 June, and 16 assessed districts. The profile labels these as period-specific arrival flows from partial monitoring coverage, not the total IDP population. UNHCR population measures and IOM ETT arrival flows are not added or treated as directly equivalent. Week 20 is linked as a source, but its figures are not displayed until extracted and validated.


The Somalia profile also presents IOM Week 19 origin-region and destination-region distributions as separate marginal summaries. Both published distributions sum to 10,451, matching the weekly arrival total. They are not bilateral origin-to-destination flows and must not be used to infer routes or pair individual origins with destinations.


### Somalia ETT snapshot validation

The Week 19 IOM ETT values are stored in `src/somalia_ett.py` as a source-attributed, manually transcribed snapshot rather than a live feed. The module provides a defensive-copy accessor and explicit checks for: weekly/cumulative count plausibility, unique district coverage, district-count consistency, origin and destination marginal totals, and cause-share arithmetic. Unit tests exercise successful validation, a deliberately corrupted distribution, district uniqueness, and mutation isolation. These checks establish internal arithmetic consistency only; they do not independently authenticate the source extraction, prove geographic completeness, or link origin and destination records into routes. Week 20 remains excluded until its numerical contents are independently extracted and verified.


The Somalia subnational page includes a Week 19 validation and provenance panel. It displays each structural/arithmetic check, identifies the source report and reporting period, and provides a JSON export containing the snapshot and validation results for reproducibility. A passed check means internal consistency only; it is not an independent source audit or confirmation of nationwide coverage.


### Somalia ETT normalized observations

The Week 19 snapshot can be represented as a long-format observation table through `src/ett_timeseries.py`. Each record retains source attribution, reporting-period dates, coverage, population group, indicator, measure type, geographic dimension, geography, value and unit. The initial release contains one verified reporting period only; it does not manufacture missing weeks or imply a complete time series. Weekly arrivals, cumulative arrivals, regional origin/destination distributions and reported reason shares remain distinct measures. Validation checks required fields, non-negative numeric values, valid period ordering and unique observation keys. The dashboard provides CSV export of these normalized records. The normalized table is a foundation for future weekly ingestion, not a claim that automated historical ingestion is already available.


A versioned baseline registry is stored at `data/somalia_ett_observations.json`. To initialize or append a reviewed batch locally:

```bash
python scripts/append_ett_report.py --initialize
python scripts/append_ett_report.py --input path/to/verified_observations.json
```

The append utility validates existing and incoming records, rejects duplicate observation keys, and never overwrites an existing observation. The JSON input must be a list of normalized records. Source verification and transcription remain a human review step; passing structural validation does not authenticate a report or its figures. Commit the reviewed registry update to preserve its version history.


### Somalia ETT trend readiness

The `src/ett_trends.py` module prepares period-comparable series for a specified indicator, measure type and geographic dimension. It withholds duplicate period keys and invalid numeric values. The dashboard displays a weekly national arrivals line chart only when at least two distinct verified reporting periods are available. Weekly flows, cumulative arrivals, reason shares and regional origin/destination marginals remain separate; no bilateral movement routes are inferred. With the current one-period baseline, the dashboard correctly reports that historical trend analysis is not yet supported.

The committed JSON registry is also checked against the Week 19 observation builder in `tests/test_ett_registry_data.py`. This guards against accidental drift between the dashboard's seed records and the reproducible source transcription.


### Somalia ETT regional and driver analysis

The `src/ett_analysis.py` module calculates ranked origin and destination distributions, percentage shares, and within-distribution concentration (HHI). It also ranks quantified displacement-reason shares. Origin and destination marginals are never joined into inferred routes. The dashboard displays the largest reported origin and destination, separate regional tables, and the quantified driver breakdown. Textual categories reported as “<1%” are not coerced to numeric zero. These are descriptive summaries of the partial Week 19 monitoring coverage, not nationwide estimates or causal attribution.


### Coverage-aware period comparison

The `src/ett_period_comparison.py` module compares the same reported regions or reason categories across two explicitly named reporting periods. It reports shared, added and removed units, and labels coverage as comparable, partial overlap or no shared units. Only shared units receive a value-change calculation; missing units are never filled with zero. A change in assessed geography is explicitly flagged so users do not mistake coverage expansion for a change in displacement patterns. This module is ready for future multi-period verified observations; it does not create a trend from the current single-period baseline.


The Streamlit Somalia ETT panel now includes a conditional regional period-comparison interface. It remains in an explanatory one-period state until at least two verified reporting periods are present. When enabled, users can select origin or destination geography and two periods, inspect changes for shared units, see coverage differences and export the comparison. New and absent regions are not imputed as zero.


### Historical ETT source register

`data/somalia_ett_source_register.json` catalogues discovered IOM DTM weekly reports, quarterly overviews and the public dataset page. It records each source URL, reporting window, source type and extraction status. The dashboard exposes this register for inspection and JSON export. Source discovery is not the same as data extraction: only Week 19 is currently marked as having normalized observations in the registry. Other weekly reports remain pending numerical transcription and validation. Quarterly aggregates are kept separate from weekly flows, and the dataset page is not treated as imported until its source file is actually ingested.


### ETT dataset ingestion gate

The public DTM dataset page identifies the June–November 2026 ETT round, its observation unit (site or location), key-informant survey method, IDP population group and partial geographic coverage. The raw downloadable file has not yet been retrieved and schema-inspected in this repository. Until that step is complete, the dashboard must not describe the dataset as imported or generate historical weekly trends from the report catalogue. The existing Week 19 normalized observations remain a separately documented, report-derived snapshot.


### Schema-first ETT dataset inspection

`src/ett_dataset_ingest.py` provides a raw-row inspection step for the downloadable location-level ETT dataset. It profiles column names, null counts, distinct values, observed Python types and exact duplicate rows. It does not infer indicator meanings, units, reporting dates, geography levels or totals from column names. Normalization is intentionally blocked until a reviewed field mapping and indicator/unit/aggregation specification are available. This prevents accidental conversion of location-level records into regional or national arrival totals.



### Somalia ETT Week 19 needs and response

The Week 19 report's needs and response tables are transcribed in `src/ett_needs.py` and displayed separately from new-arrival flow counts. The new-arrival sector table reports the share of assessed settlements where a need or response was reported; it is not the share of displaced individuals. A second table records the main needs of IDPs in assessed locations, which can describe people who arrived at any time. These measures are not combined. Text categories such as `<1%` and `Not reported` are preserved as text and are never recoded to zero. The transcription has automated structural and range checks, but those checks do not independently authenticate the source. The direct Week 19 report PDF is linked in the dashboard.

The dashboard also computes a descriptive needs-response gap in percentage points (settlement share reporting a need minus settlement share reporting a response) where both source values are numeric. It does not interpret this as a count of unmet individuals or households; non-numeric source responses remain missing from the calculation.

### DTM API access is not a substitute for the Somalia ETT dataset

IOM's current DTM API v3 is a separate data product from the public Somalia Emergency Trend Tracking (ETT) dataset. The documented API provides aggregated IDP baseline figures at Admin 0, Admin 1 and Admin 2 levels, plus a separate Humanitarian Needs Assessment (HNA) API. API v3 access requires registration and a subscription key. It should not be treated as a drop-in source for the June 2026 ETT site/location-level weekly arrival series.

- [Official DTM API overview and scope](https://dtm.iom.int/data-and-analysis/dtm-api)
- [DTM API developer portal](https://dtm-apim-portal.iom.int/)
- [Official DTM API Python client](https://github.com/Displacement-Tracking-Matrix/dtmapi)
- [Somalia ETT public dataset listing](https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0)

The project therefore keeps these sources separate. Do not replace ETT weekly observations with DTM API baseline snapshots, and do not infer weekly arrival flows from stock data. The API may be evaluated as a separate future module after its access terms, country coverage, indicator definitions and temporal granularity have been verified. The ETT importer remains schema-first and requires the actual public dataset file or a source-confirmed machine-readable endpoint before normalization.

### Optional IOM DTM API v3 connector

The repository includes an opt-in connector in `src/dtm_api.py` for aggregated IDP assessment snapshots at Admin 0, Admin 1 and Admin 2. It uses the official `dtmapi` Python client and API v3. The connector is not called by the dashboard by default and does not alter the existing ETT Week 19 snapshot or ETT historical-ingestion workflow.

To enable API calls:

1. Register at the [IOM DTM Developer Portal](https://dtm-apim-portal.iom.int/) and subscribe to API-V3.
2. Store the subscription key as `DTMAPI_SUBSCRIPTION_KEY` in your local environment or deployment secrets.
3. Use `fetch_idp_data(country_name="Somalia", admin_level=1)` from `src.dtm_api` after installing requirements.

Example:

```python
from src.dtm_api import fetch_idp_data

somalia_admin1 = fetch_idp_data(
    country_name="Somalia",
    admin_level=1,
    from_reporting_date="2025-01-01",
)
```

Admin levels: 0 = country, 1 = first-level administrative division, 2 = second-level administrative division. The API returns assessment snapshots of IDP population stocks; it is not a weekly arrival-flow feed. The HNA API is a separate service and requires its own subscription. No API key is stored in this repository. Live API results must be inspected for coverage, reporting dates, schema and duplicate/geographic consistency before publication.

Official references:
- [DTM API overview](https://dtm.iom.int/data-and-analysis/dtm-api)
- [DTM API Python client documentation](https://dtmapi.readthedocs.io/en/latest/)
- [DTM API v3 usage guide](https://dtmapi.readthedocs.io/en/latest/usage.html)


The optional `src/dtm_quality.py` helper profiles returned snapshots without altering them. It checks the expected administrative name, `reportingDate`, and `numPresentIdpInd` fields, along with missing values, invalid dates/counts, negative counts and exact duplicate rows. Its status is a basic structural/data check, not an independent validation of the source assessment. The exact API field names are based on the official DTM Python client example output.

To run a manual, read-only connection check after configuring the key:

```bash
python scripts/check_dtm_connection.py --country Somalia --admin-level 1
```

Optional date filters are available with `--from-date YYYY-MM-DD` and `--to-date YYYY-MM-DD`. The script makes no request when the key is absent, prints summary metadata rather than records, and returns a non-zero exit code when access, coverage, or basic quality checks need attention.

### DTM explorer preparation layer

`src/dtm_explorer.py` adds reusable, dashboard-ready filtering and coverage summaries for API-returned IDP assessment snapshots. It supports administrative-unit and reporting-date filters while preserving source rows and columns. It does not aggregate observations, deduplicate records, impute missing values or treat absent areas as zero.

The coverage summary reports only the geographic units and reporting dates present in the returned response. It explicitly does not claim complete national or subnational coverage. The Streamlit dashboard integration remains gated until a valid API key has been configured and live Somalia data have been reviewed.

Offline tests cover date and administrative filters, source immutability, invalid date ranges, missing geography fields and coverage wording. No live API request is made by these tests.


The Streamlit sidebar now includes an **IOM DTM API explorer** page. It is gated by the API subscription secret and makes no request until the user explicitly selects the retrieval button. The page supports Admin 0/1/2 selection, optional reporting-date filters, returned-record coverage and quality summaries, source-row inspection and CSV export. District-level responses can be filtered by returned region and district. Visualizations show individual dated assessment observations rather than summing repeated rounds. The page is separate from the UNHCR population views and the report-derived Somalia ETT panel.
