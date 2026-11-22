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
4. Deploy. No secrets are required.

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
- Week 20 report availability is linked in the app, but its numerical figures are not displayed until extracted and verified.

Sources:
- [IOM DTM Somalia](https://dtm.iom.int/somalia)
- [IOM Somalia ETT dataset](https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0)
- [IOM Week 19 ETT report](https://dtm.iom.int/reports/somalia-emergency-trend-tracking-report-week-19-31-october-04-november-2026)

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
