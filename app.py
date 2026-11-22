import pandas as pd
import plotly.express as px
import plotly.io as pio
import pycountry
import requests
import streamlit as st
from src.geo import country_iso3
from src.quality import audit_population_data, reconciliation_by_period
from src.unhcr import (
    UNHCRDataError,
    country_ranking,
    country_trend,
    explicit_global_total,
    explicit_global_total_result,
    latest_period,
    load_population_data,
    country_origin_breakdown,
    population_types,
    population_period_coverage,
    country_period_changes,
    population_measure_type,
    explicit_total_trend,
    decade_comparison,
    country_historical_comparison,
    country_profile_series,
    filter_reporting_periods,
)

st.set_page_config(page_title="Global Refugee & Displacement Intelligence", page_icon="🌍", layout="wide")

type_labels = {
    "REF_UNHCR": "Refugees under UNHCR's mandate",
    "REF_UNRWA": "Palestine refugees under UNRWA's mandate",
    "ASY": "Asylum-seekers",
    "OIP": "Other people in need of international protection",
    "IDP_UNHCR": "Internally displaced people protected/assisted by UNHCR",
    "IDP_IDMC": "Internally displaced people (IDMC data)",
    "RET": "Refugee returnees",
    "RDP": "IDP returnees",
    "NAT": "Naturalized refugees",
    "RASP": "Resettlement arrivals and sponsorship pathways",
    "STA": "Stateless people",
}

theme_palettes = {
    "Light": {"page": "#F5F7FB", "surface": "#FFFFFF", "sidebar": "#EEF2F7", "text": "#172033", "muted": "#64748B", "accent": "#2563EB", "border": "#DCE3ED", "plotly": "plotly_white"},
    "Green": {"page": "#F1F7F1", "surface": "#FFFFFF", "sidebar": "#E5F0E5", "text": "#183528", "muted": "#5C7566", "accent": "#238653", "border": "#D1E2D4", "plotly": "plotly_white"},
    "Dark": {"page": "#101722", "surface": "#182332", "sidebar": "#131E2B", "text": "#E8EEF7", "muted": "#A6B4C6", "accent": "#62A8FF", "border": "#2B3B4E", "plotly": "plotly_dark"},
    "Ocean": {"page": "#EDF5F8", "surface": "#FFFFFF", "sidebar": "#DDECF2", "text": "#123044", "muted": "#557386", "accent": "#087E9B", "border": "#C9DEE7", "plotly": "plotly_white"},
}

with st.sidebar:
    st.header("Appearance")
    selected_theme = st.selectbox(
        "Dashboard theme", list(theme_palettes), index=0,
        help="Choose a colour theme for the dashboard. Your selection applies immediately.",
    )
    st.caption("Change the visual style without changing the underlying data.")
    st.divider()
    st.header("Filters")
    selected_type = st.selectbox(
        "Population category",
        population_types(),
        index=0,
        format_func=lambda code: type_labels.get(code, code),
    )
    role = st.radio("Country view", ["Countries of asylum / hosting", "Countries of origin"])
    analysis_view = st.radio(
        "Analysis page",
        ["Country explorer", "Global hosting comparison", "Global hosting map", "Historical change analysis", "Country historical comparison", "Country profile comparison", "Global displacement trends", "Displacement pressure signals", "Somalia displacement profile", "Somalia subnational data"],
        help="Compare country totals across all available hosting countries.",
    )

palette = theme_palettes[selected_theme]
pio.templates.default = palette["plotly"]
st.markdown(
    f"""
    <style>
    :root {{
      --dash-page:{palette["page"]}; --dash-surface:{palette["surface"]};
      --dash-sidebar:{palette["sidebar"]}; --dash-text:{palette["text"]};
      --dash-muted:{palette["muted"]}; --dash-accent:{palette["accent"]};
      --dash-border:{palette["border"]};
    }}
    .stApp,[data-testid="stAppViewContainer"]{{background:var(--dash-page);color:var(--dash-text)}}
    [data-testid="stHeader"]{{background:transparent}}
    [data-testid="stSidebar"]>div:first-child{{background:var(--dash-sidebar);border-right:1px solid var(--dash-border)}}
    [data-testid="stSidebar"] *{{color:var(--dash-text)}}
    .block-container{{max-width:1480px;padding-top:1.6rem;padding-bottom:3rem}}
    [data-testid="stMarkdownContainer"],[data-testid="stText"],.stMarkdown,p,label,h1,h2,h3,h4{{color:var(--dash-text)}}
    [data-testid="stCaptionContainer"],small{{color:var(--dash-muted)!important}}
    [data-testid="stMetric"]{{background:var(--dash-surface);border:1px solid var(--dash-border);border-radius:14px;padding:16px 18px;box-shadow:0 3px 14px rgba(15,23,42,.045)}}
    [data-testid="stMetricLabel"] p{{color:var(--dash-muted)!important;font-weight:600}}
    [data-testid="stMetricValue"]{{color:var(--dash-text);font-weight:750}}
    [data-testid="stExpander"],[data-testid="stDataFrame"],[data-testid="stTable"]{{border-color:var(--dash-border);border-radius:12px}}
    div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,.stTextInput input{{background:var(--dash-surface);border-color:var(--dash-border);color:var(--dash-text);border-radius:10px}}
    .stButton>button,.stDownloadButton>button,.stLinkButton>a{{border-radius:10px;border:1px solid var(--dash-accent);color:var(--dash-accent);font-weight:650;transition:all 140ms ease}}
    .stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{{background:var(--dash-accent);color:white;border-color:var(--dash-accent)}}
    hr{{border-color:var(--dash-border)}} [data-testid="stAlert"]{{border-radius:12px}}
    .dashboard-hero{{background:linear-gradient(120deg,var(--dash-surface),var(--dash-sidebar));border:1px solid var(--dash-border);border-left:5px solid var(--dash-accent);border-radius:18px;padding:22px 26px;margin:0 0 22px;box-shadow:0 5px 20px rgba(15,23,42,.045)}}
    .dashboard-hero h1{{margin:0 0 7px;font-size:clamp(1.55rem,2.8vw,2.25rem);line-height:1.2;color:var(--dash-text);letter-spacing:-.035em}}
    .dashboard-hero p{{margin:0;color:var(--dash-muted);font-size:.98rem}}
    .theme-chip{{display:inline-block;margin-top:14px;padding:5px 10px;border-radius:999px;background:var(--dash-sidebar);border:1px solid var(--dash-border);color:var(--dash-accent);font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase}}
    </style>
    <section class="dashboard-hero">
      <h1>🌍 Global Refugee &amp; Displacement Intelligence</h1>
      <p>Explore official displacement statistics, country profiles and humanitarian trends.</p>
      <span class="theme-chip">{selected_theme} theme</span>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.spinner("Retrieving UNHCR population history from 1960 onward..."):
    try:
        df = load_population_data(selected_type)
    except UNHCRDataError as exc:
        st.error(str(exc))
        st.info("The dashboard uses UNHCR's public, unauthenticated JSON data API. No API key or account is required.")
        st.link_button("UNHCR API documentation", "https://refugeedata.unhcr.org/en/documentation/technical-reference/api/")
        st.stop()
    except Exception as exc:
        st.error(f"Unexpected data-loading error: {type(exc).__name__}: {exc}")
        st.stop()

all_periods = sorted(df["time_period"].dropna().astype(str).unique())
if not all_periods:
    st.error("UNHCR returned no reporting periods for this population category.")
    st.stop()

with st.sidebar:
    st.divider()
    st.subheader("Historical period range")
    st.caption("Limit the analysis to an inclusive range. The source data remains unchanged.")
    range_start = st.selectbox(
        "From period",
        all_periods,
        index=0,
        key=f"history_start_{selected_type}",
    )
    eligible_end_periods = [period for period in all_periods if period >= range_start]
    range_end = st.selectbox(
        "To period",
        eligible_end_periods,
        index=len(eligible_end_periods) - 1,
        key=f"history_end_{selected_type}",
    )

df = filter_reporting_periods(df, range_start, range_end)
periods = sorted(df["time_period"].dropna().astype(str).unique())
if not periods:
    st.error("No observations are available inside the selected historical range.")
    st.stop()

selected_period = st.selectbox("Reporting period", periods, index=len(periods) - 1)
geo = (
    "ref_area_adm0"
    if analysis_view in ("Global hosting comparison", "Global hosting map") or role == "Countries of asylum / hosting"
    else "area_ori_adm0"
)

global_total, global_total_status = explicit_global_total_result(df, selected_type, selected_period)
a, b, c = st.columns(3)
a.metric("Source-reported global total", f"{global_total:,.0f}" if global_total is not None else "Unavailable")
b.metric("Selected period", selected_period)
c.metric("Records retrieved", f"{len(df):,}")

total_status_messages = {
    "reported": "A unique explicit global total is available in the source data for this category and period.",
    "not_reported": "UNHCR has not supplied an explicit global-total record for this category and period in the retrieved data. Country-level records, where available, are shown separately and are not summed to manufacture a global total.",
    "ambiguous": "More than one distinct explicit global-total value was found. The dashboard withholds the figure pending source-level verification.",
    "reported_without_value": "A global-total record exists, but its reported value is missing or non-numeric.",
    "unavailable_geography": "The retrieved data do not include the geographic dimensions needed to identify an explicit global total.",
    "unavailable_schema": "The retrieved data are missing required fields for validating an explicit global total.",
}
if global_total_status == "reported":
    st.caption(total_status_messages[global_total_status])
else:
    st.info(total_status_messages.get(global_total_status, "An explicit global total could not be validated from the retrieved source records."))

st.caption(f"Source history starts at 1960 · Selected analysis range: {range_start} to {range_end} · Latest period in range: {latest_period(df) or 'Unknown'}")

# Data quality diagnostics for the currently selected population category.
quality = audit_population_data(df)
with st.expander("Data Quality & Sources", expanded=False):
    st.caption("Automated checks on retrieved records. These diagnostics flag issues; they do not silently repair or aggregate source data.")
    if quality["status"] != "ok":
        st.error("The retrieved dataset does not contain the minimum required schema.")
        st.write("Missing fields:", ", ".join(quality["missing_columns"]))
    else:
        q1, q2, q3 = st.columns(3)
        q1.metric("Invalid population values", f"{quality['invalid_population_values']:,}")
        q2.metric("Negative population values", f"{quality['negative_population_values']:,}")
        q3.metric("Missing geography codes", f"{quality['missing_geography_codes']:,}")
        q4, q5 = st.columns(2)
        q4.metric("Duplicate dimension-key rows", f"{quality['duplicate_dimension_key_rows']:,}")
        q5.metric("Duplicate key groups", f"{quality['duplicate_dimension_key_groups']:,}")
        st.caption("Dimension keys checked: population type, reporting period, hosting-country code and origin-country code. Duplicate keys are flagged, not summed.")
        issue_keys = ("invalid_population_values", "negative_population_values", "missing_geography_codes", "duplicate_dimension_key_rows")
        if any(quality[key] > 0 for key in issue_keys):
            st.warning("One or more checks flagged records. Review source observations before interpreting results.")
        else:
            st.success("No issues were detected by these checks in the retrieved dataset.")
    st.markdown("**Source:** [UNHCR Population Statistics](https://refugeedata.unhcr.org/en/data-finder/detail/PopStatsOfficial/data/)  \\n**API:** [UNHCR technical reference](https://refugeedata.unhcr.org/en/documentation/technical-reference/api/)")
    st.caption(f"Retrieved records: {len(df):,} · Selected reporting period: {selected_period}")

    st.markdown("**Historical reporting-period coverage**")
    st.caption("This query retrieves the available historical periods for the selected category using a compact population-type/time-period response. It reports observed periods; it does not assume that every category follows the same reporting frequency.")
    with st.spinner("Checking historical reporting-period coverage..."):
        try:
            coverage = population_period_coverage(selected_type)
        except UNHCRDataError as exc:
            st.warning(f"Historical coverage could not be retrieved: {exc}")
            coverage = pd.DataFrame()
    if coverage.empty:
        st.info("No historical reporting-period coverage records were returned.")
    else:
        first_period = str(coverage["time_period"].iloc[0])
        last_period = str(coverage["time_period"].iloc[-1])
        h1, h2, h3 = st.columns(3)
        h1.metric("Periods available", f"{len(coverage):,}")
        h2.metric("Earliest period", first_period)
        h3.metric("Latest period", last_period)
        coverage_fig = px.bar(
            coverage,
            x="time_period",
            y="record_count",
            labels={"time_period": "Reporting period", "record_count": "Observations"},
            title="UNHCR observations by reporting period",
        )
        coverage_fig.update_layout(xaxis_tickangle=-45, height=360)
        st.plotly_chart(coverage_fig, use_container_width=True)
        st.dataframe(coverage, hide_index=True, use_container_width=True)
        coverage_export = coverage.copy()
        coverage_export.insert(0, "population_category", selected_type)
        st.download_button(
            "Download historical coverage (CSV)",
            data=coverage_export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"unhcr_period_coverage_{selected_type}.csv",
            mime="text/csv",
        )
        st.caption("Interpretation: a period absent from this response is an unobserved period in this query, not proof that the population was zero or that UNHCR failed to report. Reporting cadence can vary by population category.")

    st.markdown("**Period reconciliation (diagnostic only)**")
    reconciliation = reconciliation_by_period(df, "ref_area_adm0")
    if reconciliation.empty:
        st.info("The available fields are insufficient for period reconciliation.")
    else:
        st.caption("Compares an explicit UNHCR total row with distinct country-level hosting records. A country sum is not an official global total and is never substituted for a missing source total.")
        st.dataframe(reconciliation, hide_index=True, use_container_width=True)
        st.download_button(
            "Download reconciliation report (CSV)",
            data=reconciliation.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"unhcr_reconciliation_{selected_type}.csv",
            mime="text/csv",
        )
        if reconciliation["status"].eq("duplicate_country_keys").any():
            st.warning("Some periods contain repeated country keys; country sums are withheld for those periods.")
        if reconciliation["status"].eq("no_unique_explicit_total").any():
            st.info("Some periods have no unique explicit global total. Their country sums are not promoted to global totals.")
st.divider()
ranking = country_ranking(
    df, selected_type, geo, selected_period,
    limit=200 if analysis_view in ("Global hosting comparison", "Global hosting map") else 20,
)

if analysis_view == "Country historical comparison":
    st.header("Country historical comparison")
    st.caption(
        "Compare reported country totals over the selected historical window. "
        "Countries are compared within the selected geography; hosting and origin dimensions are never mixed."
    )
    opposite = "area_ori_adm0" if geo == "ref_area_adm0" else "ref_area_adm0"
    label_col = f"{geo}_label"
    if geo not in df.columns or opposite not in df.columns:
        st.warning("The retrieved records do not contain the dimensions needed for this comparison.")
        st.stop()
    options_frame = df[
        df["pop_type"].astype("string").eq(selected_type)
        & df[opposite].astype("string").eq("_T")
        & df[geo].notna()
        & ~df[geo].astype("string").isin(["_T", "_X"])
    ][[geo] + ([label_col] if label_col in df.columns else [])].drop_duplicates()
    options_frame["country_code"] = options_frame[geo].astype(str)
    options_frame["country_name"] = options_frame[label_col] if label_col in options_frame.columns else options_frame["country_code"]
    options_frame = options_frame.drop_duplicates("country_code").sort_values("country_name")
    code_to_name = dict(zip(options_frame["country_code"], options_frame["country_name"]))
    ranked_codes = []
    current_ranking = country_ranking(df, selected_type, geo, selected_period, limit=200)
    if not current_ranking.empty:
        name_to_code = {str(name): code for code, name in code_to_name.items()}
        ranked_codes = [name_to_code[name] for name in current_ranking["country"] if name in name_to_code]
    defaults = ranked_codes[:3]
    selected_codes = st.multiselect(
        "Select countries to compare",
        options=options_frame["country_code"].tolist(),
        default=defaults,
        format_func=lambda code: code_to_name.get(code, code),
        max_selections=8,
        help="Choose up to eight countries. Countries without observations in a period are left missing, not set to zero.",
    )
    if not selected_codes:
        st.info("Select at least one country to display its historical series.")
        st.stop()
    comparison = country_historical_comparison(df, selected_type, geo, selected_codes)
    if comparison.empty:
        st.warning("No unambiguous country-period totals were found for this selection.")
        st.stop()
    comparison["country"] = comparison["country"].astype(str)
    measure = population_measure_type(selected_type)
    st.caption(
        f"Geography: {'Hosting / country of asylum' if geo == 'ref_area_adm0' else 'Country of origin'} · "
        f"Measure: {measure.title()} · Window: {range_start} to {range_end}"
    )
    series_count = comparison.groupby("country_code")["time_period"].nunique()
    m1, m2, m3 = st.columns(3)
    m1.metric("Countries selected", f"{comparison['country_code'].nunique():,}")
    m2.metric("Observed reporting periods", f"{comparison['time_period'].nunique():,}")
    m3.metric("Country-period observations", f"{len(comparison):,}")
    trend_fig = px.line(
        comparison, x="time_period", y="population", color="country",
        markers=True,
        labels={"time_period": "Reporting period", "population": "People", "country": "Country"},
        title="Historical country comparison",
    )
    trend_fig.update_layout(yaxis_tickformat=",", xaxis_tickangle=-45, legend_title_text="Country")
    st.plotly_chart(trend_fig, use_container_width=True)
    coverage_table = pd.DataFrame([
        {"country": code_to_name.get(code, code), "observed_periods": int(count)}
        for code, count in series_count.items()
    ]).sort_values("country")
    st.subheader("Reporting coverage by country")
    st.dataframe(coverage_table, hide_index=True, use_container_width=True)
    st.subheader("Comparable country-period observations")
    st.dataframe(comparison, hide_index=True, use_container_width=True)
    st.download_button(
        "Download country comparison (CSV)",
        data=comparison.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"country_historical_comparison_{selected_type}.csv",
        mime="text/csv",
    )
    if measure == "stock":
        st.info("This is a stock comparison. Each point is a reported population at a point in time; do not add values across periods.")
    else:
        st.info("This is a flow comparison. Each point is a period-specific flow. Missing periods are not zero, and values should not be interpreted as a population stock.")
    st.caption("Only unique country-period totals with the opposite geography set to the source total code are included. Duplicate country-period keys are withheld rather than summed. Gaps indicate missing or ambiguous observations, not zero population.")
    st.stop()

if analysis_view == "Country profile comparison":
    st.header("Country profile comparison")
    st.caption(
        "Build a multi-indicator historical profile for one country. Population categories remain separate; "
        "the dashboard does not add refugees, IDPs or asylum-seekers together."
    )
    opposite = "area_ori_adm0" if geo == "ref_area_adm0" else "ref_area_adm0"
    if geo not in df.columns or opposite not in df.columns:
        st.warning("The retrieved data do not contain the dimensions required for a country profile.")
        st.stop()
    country_options = df[
        df["pop_type"].astype("string").eq(selected_type)
        & df[opposite].astype("string").eq("_T")
        & df[geo].notna()
        & ~df[geo].astype("string").isin(["_T", "_X"])
    ][[geo] + ([f"{geo}_label"] if f"{geo}_label" in df.columns else [])].drop_duplicates()
    country_options["country_code"] = country_options[geo].astype(str)
    label_col = f"{geo}_label"
    country_options["country_name"] = country_options[label_col] if label_col in country_options.columns else country_options["country_code"]
    country_options = country_options.drop_duplicates("country_code").sort_values("country_name")
    if country_options.empty:
        st.warning("No country totals are available for the selected geography and population category.")
        st.stop()
    country_map = dict(zip(country_options["country_code"], country_options["country_name"]))
    selected_country = st.selectbox(
        "Select country",
        country_options["country_code"].tolist(),
        format_func=lambda code: country_map.get(code, code),
    )
    available_categories = [
        "REF_UNHCR", "REF_UNRWA", "ASY", "OIP",
        "IDP_UNHCR", "IDP_IDMC", "RET", "RDP", "NAT", "RASP", "STA",
    ]
    default_categories = [code for code in [selected_type, "ASY", "IDP_UNHCR"] if code in available_categories]
    selected_categories = st.multiselect(
        "Population indicators",
        options=available_categories,
        default=list(dict.fromkeys(default_categories)),
        format_func=lambda code: type_labels.get(code, code),
        help="Select indicators to profile. Each category is reported separately and is never combined into a single population total.",
    )
    if not selected_categories:
        st.info("Select at least one population indicator.")
        st.stop()
    category_frames = {}
    category_errors = {}
    for category in selected_categories:
        try:
            category_frame = df.copy() if category == selected_type else load_population_data(category)
            category_frames[category] = filter_reporting_periods(category_frame, range_start, range_end)
        except Exception as exc:
            category_errors[category] = f"{type(exc).__name__}: {exc}"
    if category_errors:
        for category, error in category_errors.items():
            st.warning(f"{type_labels.get(category, category)} could not be loaded: {error}")
    profile = country_profile_series(category_frames, selected_country, geo)
    if profile.empty:
        st.warning("No unambiguous country-level observations were found for the selected indicators and period range.")
        st.stop()
    st.caption(
        f"Country: {country_map.get(selected_country, selected_country)} · "
        f"Geography: {'Hosting / country of asylum' if geo == 'ref_area_adm0' else 'Country of origin'} · "
        f"Period range: {range_start} to {range_end}"
    )
    latest_rows = (
        profile.sort_values("time_period")
        .groupby("pop_type", as_index=False)
        .tail(1)
        .sort_values("pop_type")
    )
    st.subheader("Latest observed value by indicator")
    metric_cols = st.columns(min(3, len(latest_rows)))
    for index, (_, row) in enumerate(latest_rows.iterrows()):
        with metric_cols[index % len(metric_cols)]:
            st.metric(
                type_labels.get(row["pop_type"], row["pop_type"]),
                f"{row['population']:,.0f}",
                help=f"Latest observed reporting period: {row['time_period']} · {row['measure_type'].title()} measure",
            )
            st.caption(f"Reporting period: {row['time_period']}")
    st.subheader("Historical profile")
    st.caption("Each indicator has its own panel and vertical scale so that differences in magnitude do not hide smaller series. Gaps are not imputed.")
    profile_fig = px.line(
        profile,
        x="time_period",
        y="population",
        color="pop_type",
        facet_row="pop_type",
        markers=True,
        labels={"time_period": "Reporting period", "population": "People", "pop_type": "Indicator"},
        category_orders={"pop_type": selected_categories},
    )
    profile_fig.for_each_annotation(lambda annotation: annotation.update(text=type_labels.get(annotation.text.split("=")[-1], annotation.text)))
    profile_fig.update_yaxes(matches=None, tickformat=",")
    profile_fig.update_layout(height=max(420, 230 * profile["pop_type"].nunique()), showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(profile_fig, use_container_width=True)
    st.subheader("Observed data and coverage")
    coverage = (
        profile.groupby(["pop_type", "measure_type"], as_index=False)
        .agg(observed_periods=("time_period", "nunique"), first_period=("time_period", "min"), latest_period=("time_period", "max"))
    )
    coverage["population_category"] = coverage["pop_type"].map(type_labels)
    st.dataframe(coverage[["population_category", "measure_type", "observed_periods", "first_period", "latest_period"]], hide_index=True, use_container_width=True)
    st.dataframe(profile, hide_index=True, use_container_width=True)
    st.download_button(
        "Download country profile (CSV)",
        data=profile.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"country_profile_{selected_country}.csv",
        mime="text/csv",
    )
    st.info("Stock indicators describe populations at a point in time; flow indicators describe events or movements during a period. Do not add category values together or compare them as if they were the same measure. Missing periods are not zero. Duplicate country-period totals are withheld.")
    st.stop()

if analysis_view == "Global displacement trends":
    st.header("Global displacement trends")
    measure = population_measure_type(selected_type)
    if measure == "stock":
        st.info(
            "This category is a **stock**: it measures people with the characteristic at a point in time. "
            "Values across reporting periods must not be added together."
        )
    else:
        st.info(
            "This category is a **flow**: it measures people who acquired the characteristic during a period. "
            "UNHCR identifies this category as part of its solutions-related flow statistics."
        )
    st.caption(
        f"Selected series: {type_labels.get(selected_type, selected_type)} · "
        f"Measure type: {measure.title()}"
    )
    trend_data = explicit_total_trend(df, selected_type)
    if trend_data.empty:
        st.warning(
            "No unique explicit total rows are available across the retrieved reporting periods. "
            "Country totals are not added to manufacture a global trend."
        )
    else:
        st.metric("Periods with explicit totals", f"{len(trend_data):,}")
        trend_fig = px.line(
            trend_data, x="time_period", y="population", markers=True,
            labels={"time_period": "Reporting period", "population": "People"},
            title=f"Explicit UNHCR total — {type_labels.get(selected_type, selected_type)}",
        )
        trend_fig.update_layout(yaxis_tickformat=",", xaxis_tickangle=-45)
        st.plotly_chart(trend_fig, use_container_width=True)

        st.subheader("Decade-level comparison")
        decade_data = decade_comparison(df, selected_type)
        if decade_data.empty:
            st.info("There are not enough explicit global totals to prepare a decade comparison.")
        else:
            if measure == "stock":
                st.caption("For each decade, this shows the last observed explicit global total. Stock values are not added across years.")
                decade_title = "Last observed global stock by decade"
            else:
                st.caption("For each decade, this shows the mean of observed period-specific explicit flows. It is not a cumulative decade total; reporting periods may vary in length and frequency.")
                decade_title = "Mean observed period-specific flow by decade"
            decade_fig = px.bar(
                decade_data, x="decade", y="population",
                labels={"decade": "Decade", "population": "People"},
                title=decade_title,
                hover_data=["observed_periods", "summary_method"],
            )
            decade_fig.update_layout(yaxis_tickformat=",")
            st.plotly_chart(decade_fig, use_container_width=True)
            st.dataframe(decade_data, hide_index=True, use_container_width=True)
            st.download_button(
                "Download decade comparison (CSV)",
                data=decade_data.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"decade_comparison_{selected_type}.csv",
                mime="text/csv",
            )
        st.dataframe(trend_data, hide_index=True, use_container_width=True)
        export = trend_data.copy()
        export.insert(0, "measure_type", measure)
        export.insert(0, "population_category", selected_type)
        st.download_button(
            "Download global trend data (CSV)",
            data=export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"global_trend_{selected_type}.csv",
            mime="text/csv",
        )
    st.caption(
        "Only explicit, unambiguous total rows are plotted. If the source does not supply a total, "
        "the dashboard leaves the period out rather than summing country values. For flow categories, "
        "each point is a period-specific flow; the chart is not a cumulative total."
    )
    st.stop()




if analysis_view == "Somalia subnational data":
    st.header("Somalia subnational displacement data")
    st.caption(
        "A source and coverage workspace for district- and location-level displacement evidence. "
        "This page distinguishes broad baseline coverage from the narrower, frequently updated ETT series."
    )

    st.subheader("Latest IOM DTM Emergency Trend Tracking")
    st.markdown(
        "**Coverage period:** 14 June – 11 November 2026  \n"
        "**Data collection:** weekly key-informant interviews at location level  \n"
        "**Population group:** IDPs  \n"
        "**Geographical coverage:** partial, not nationwide."
    )
    st.info(
        "IOM reports that the ETT series expanded in October 2026 to 16 districts. "
        "Coverage varies by reporting week and assessment round; an unassessed district "
        "must not be interpreted as having zero displacement."
    )
    st.link_button(
        "Open official IOM DTM ETT dataset",
        "https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0",
    )
    st.link_button(
        "Open Week 20 report (7–11 Nov 2026; report mirror)",
        "https://humara.org/report/2552b18b-af4f-490f-805c-a005a3b012ba",
    )
    st.link_button(
        "Open Week 19 report (31 Oct – 4 Nov 2026; latest verified figures)",
        "https://dtm.iom.int/reports/somalia-emergency-trend-tracking-report-week-19-31-october-04-november-2026",
    )
    st.link_button(
        "Open Somalia DTM country page and latest reports",
        "https://dtm.iom.int/somalia",
    )

    st.markdown("**Latest numerically verified ETT figures — Week 19**")
    st.info(
        "IOM has published Week 20 (7–11 November 2026) for the same 16-district " 
        "monitoring footprint. Its numerical figures have not yet been extracted " 
        "and verified for this dashboard, so Week 19 remains the latest displayed snapshot."
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("New arrivals this week", "10,451")
    m2.metric("Cumulative arrivals since June", "114,553")
    m3.metric("Districts assessed", "16")
    st.caption("These are new-arrival flow measures, not the total number of IDPs currently living in Somalia.")

    with st.expander("ETT reporting coverage and historical context"):
        coverage_phases = pd.DataFrame({
            "Coverage phase": [
                "Initial June 2026 series",
                "Expanded coverage: July–September 2026",
                "Expanded coverage from 17 October 2026",
                "Week 19 reporting period",
                "Week 20 reporting period",
            ],
            "Coverage detail": [
                "5 districts: Baidoa, Dayniile, Diinsoor, Doolow and Kahda",
                "8 additional districts were phased in; up to 13 districts in total",
                "11 additional districts were added, expanding the series to 16 districts",
                "16 districts assessed",
                "16 districts assessed; numerical figures not yet integrated into this dashboard",
            ],
            "Reference": [
                "14 June 2026",
                "27 July–2 September 2026",
                "From 17 October 2026",
                "31 October–4 November 2026",
                "7–11 November 2026 (IOM report published 18 November 2026)",
            ],
        })
        st.dataframe(coverage_phases, hide_index=True, use_container_width=True)
        st.markdown(
            "**Separate quarterly context (Q3 2026):** IOM reported 68,469 new arrivals "
            "during July–September 2026; drought accounted for 56%, conflict 33% and "
            "evictions 9%. This quarterly figure is not added to Week 19 and is not "
            "presented as a directly comparable weekly observation."
        )
        st.caption(
            "Coverage changed over time. Differences between reporting periods may reflect "
            "both displacement patterns and changes in the districts assessed. The Q3 "
            "quarterly summary and the June–November ETT series are retained as distinct "
            "source periods and are not merged into one continuous weekly trend."
        )
        st.link_button(
            "Open IOM Q3 2026 ETT overview",
            "https://dtm.iom.int/domain/displacementiomint",
        )
        st.link_button(
            "Open IOM June–November 2026 ETT dataset",
            "https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0",
        )

    causes = pd.DataFrame({
        "Reason": ["Conflict", "Floods", "Drought", "Evictions"],
        "Share (%)": [44, 31, 20, 5],
    })
    st.plotly_chart(
        px.bar(causes, x="Reason", y="Share (%)", title="Reported reasons for new displacement — Week 19"),
        use_container_width=True,
    )
    st.caption(
        "The report separately records other hazards as <1% and other reasons as <1%. "
        "These categories are shown as reported text rather than being converted to 0%."
    )
    monitored_districts = [
        "Afgooye", "Afmadow", "Baardheere", "Baidoa", "Balcad", "Belet Weyne",
        "Bulo Burto", "Dayniile", "Diinsoor", "Doolow", "Jalalaqsi", "Jowhar",
        "Kahda", "Kismaayo", "Luuq", "Qansax Dheere",
    ]
    with st.expander("View the 16 districts monitored in Week 19"):
        st.write(", ".join(monitored_districts))
        st.caption(
            "This is the reporting coverage list, not a ranking. District-level arrival "
            "counts are not displayed here because the currently integrated table contains "
            "regional destination totals only."
        )
    destinations = pd.DataFrame({
        "Destination region": ["Gedo", "Bay", "Banadir", "Middle Shabelle", "Hiraan", "Lower Juba", "Lower Shabelle"],
        "New arrivals": [2188, 1985, 1929, 1883, 1041, 769, 656],
    }).sort_values("New arrivals", ascending=False)
    st.markdown("**Reported destination regions — Week 19**")
    st.caption(
        "The map joins the seven published destination-region counts to a separate "
        "administrative-boundary reference layer. Regions without a reported Week 19 "
        "count remain unshaded; they are not interpreted as zero."
    )

    @st.cache_data(ttl=86400, show_spinner=False)
    def load_somalia_admin1_geojson():
        boundary_url = (
            "https://services.arcgis.com/HwB9RoolJXJlKJ40/ArcGIS/rest/services/"
            "Som_Admbnda_Adm1_UNDP/FeatureServer/6/query"
        )
        response = requests.get(
            boundary_url,
            params={
                "where": "1=1",
                "outFields": "ADM1_EN,ADM1_PCODE",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            },
            timeout=30,
        )
        response.raise_for_status()
        geojson = response.json()
        if geojson.get("type") != "FeatureCollection" or not geojson.get("features"):
            raise ValueError("The administrative-boundary service returned no GeoJSON features.")
        return geojson

    region_boundary_names = {
        "Gedo": "Gedo",
        "Bay": "Bay",
        "Banadir": "Banaadir",
        "Middle Shabelle": "Middle Shabelle",
        "Hiraan": "Hiiraan",
        "Lower Juba": "Lower Juba",
        "Lower Shabelle": "Lower Shabelle",
    }
    map_data = destinations.copy()
    map_data["Boundary region"] = map_data["Destination region"].map(region_boundary_names)
    try:
        somalia_geojson = load_somalia_admin1_geojson()
        boundary_names = {
            str(feature.get("properties", {}).get("ADM1_EN", "")).strip().casefold()
            for feature in somalia_geojson["features"]
        }
        map_data = map_data[
            map_data["Boundary region"].str.casefold().isin(boundary_names)
        ].copy()
        matched_count = len(map_data)
        match_col, total_col = st.columns(2)
        match_col.metric("Destination regions matched", f"{matched_count} / {len(destinations)}")
        total_col.metric("Regions in boundary layer", f"{len(boundary_names):,}")
        if matched_count == len(destinations):
            st.success("All seven reported destination regions matched the administrative boundary layer.")
        else:
            missing_matches = sorted(
                set(destinations["Destination region"]) - set(map_data["Destination region"])
            )
            st.warning(
                "Some published destination names could not be matched to the boundary "
                f"layer and were withheld from the map: {', '.join(missing_matches)}."
            )
        if not map_data.empty:
            regional_map = px.choropleth(
                map_data,
                geojson=somalia_geojson,
                locations="Boundary region",
                featureidkey="properties.ADM1_EN",
                color="New arrivals",
                hover_name="Destination region",
                hover_data={"New arrivals": ":,", "Boundary region": False},
                color_continuous_scale="YlOrRd",
                title="New arrivals by destination region — Week 19",
            )
            regional_map.update_geos(
                fitbounds="locations",
                visible=False,
                showcountries=True,
                showcoastlines=True,
            )
            regional_map.update_layout(
                height=620,
                margin={"l": 0, "r": 0, "t": 55, "b": 0},
                coloraxis_colorbar_title="New arrivals",
            )
            st.plotly_chart(regional_map, use_container_width=True)
        else:
            st.warning("No destination regions could be matched to the boundary layer.")
    except (requests.RequestException, ValueError, KeyError) as exc:
        st.warning(
            "The regional map could not be loaded from the boundary service. "
            f"The source table remains available below. Details: {exc}"
        )
    st.dataframe(destinations, hide_index=True, use_container_width=True)
    st.caption(
        "The published report gives destination-region counts. These are not district totals. "
        "Do not infer district-level values from regional counts."
    )
    st.download_button(
        "Download Week 19 destination data (CSV)",
        data=destinations.to_csv(index=False).encode("utf-8-sig"),
        file_name="somalia_ett_week19_destination_regions.csv",
        mime="text/csv",
    )
    destination_total = int(destinations["New arrivals"].sum())
    st.metric("Sum of reported destination counts", f"{destination_total:,}")
    if destination_total != 10451:
        st.warning(
            "The published destination-region counts do not reconcile to the Week 19 "
            "headline total; review the source report before interpreting the difference."
        )
    else:
        st.caption(
            "The seven reported destination-region counts sum to the Week 19 headline "
            "total of 10,451. This arithmetic check does not establish individual routes."
        )

    origins = pd.DataFrame({
        "Origin": [
            "Bay", "Middle Shabelle", "Hiraan", "Gedo", "Lower Shabelle",
            "Bakool", "Banadir", "Lower Juba", "Middle Juba", "Ethiopia",
        ],
        "New arrivals": [3528, 1862, 1105, 875, 789, 760, 472, 512, 375, 173],
    }).sort_values("New arrivals", ascending=False)
    origin_total = int(origins["New arrivals"].sum())
    st.markdown("**Reported origins of new arrivals — Week 19**")
    st.caption(
        "Origin counts are presented separately from destination counts. They describe "
        "different sides of the movement record and must not be added together."
    )
    st.metric("Sum of reported origin counts", f"{origin_total:,}")
    st.plotly_chart(
        px.bar(
            origins,
            x="New arrivals",
            y="Origin",
            orientation="h",
            title="Reported origins of new arrivals — Week 19",
            text="New arrivals",
        ).update_layout(height=430, yaxis={"categoryorder": "total ascending"}),
        use_container_width=True,
    )
    st.dataframe(origins, hide_index=True, use_container_width=True)
    st.download_button(
        "Download Week 19 origin data (CSV)",
        data=origins.to_csv(index=False).encode("utf-8-sig"),
        file_name="somalia_ett_week19_origin_regions.csv",
        mime="text/csv",
    )
    if origin_total != 10451:
        st.warning(
            "The published origin counts do not reconcile to the weekly headline total; "
            "review the source report before interpreting the difference."
        )
    else:
        st.caption(
            "The ten reported origin counts sum to the Week 19 headline total of 10,451. "
            "This arithmetic check does not imply that every origin is within Somalia; "
            "Ethiopia is a reported cross-border origin."
        )

    st.subheader("Week 19 consistency audit")
    consistency_checks = pd.DataFrame([
        {
            "Check": "Reported origin counts",
            "Observed": f"{origin_total:,}",
            "Reference": "10,451 headline arrivals",
            "Result": "Pass" if origin_total == 10451 else "Review",
        },
        {
            "Check": "Reported destination counts",
            "Observed": f"{destination_total:,}",
            "Reference": "10,451 headline arrivals",
            "Result": "Pass" if destination_total == 10451 else "Review",
        },
        {
            "Check": "Reported displacement-cause shares",
            "Observed": f"{causes['Share (%)'].sum():.0f}%",
            "Reference": "100% across four displayed causes",
            "Result": "Pass" if causes["Share (%)"].sum() == 100 else "Review",
        },
    ])
    st.dataframe(consistency_checks, hide_index=True, use_container_width=True)
    if consistency_checks["Result"].eq("Review").any():
        st.warning(
            "At least one arithmetic check does not match its reference. "
            "Review the underlying report before drawing conclusions."
        )
    else:
        st.caption(
            "All three arithmetic checks reconcile. These checks confirm internal sums only; "
            "they do not verify person-level uniqueness, route linkages, or completeness beyond "
            "the published reporting coverage."
        )
    st.download_button(
        "Download Week 19 consistency audit (CSV)",
        data=consistency_checks.to_csv(index=False).encode("utf-8-sig"),
        file_name="somalia_ett_week19_consistency_audit.csv",
        mime="text/csv",
    )

    st.subheader("Origin and destination profile — Week 19")
    origin_col, destination_col = st.columns(2)
    origin_col.metric(
        "Largest reported origin",
        str(origins.iloc[0]["Origin"]),
        f'{int(origins.iloc[0]["New arrivals"]):,} arrivals',
    )
    destination_col.metric(
        "Largest reported destination",
        str(destinations.iloc[0]["Destination region"]),
        f'{int(destinations.iloc[0]["New arrivals"]):,} arrivals',
    )
    origin_chart = px.bar(
        origins,
        x="New arrivals",
        y="Origin",
        orientation="h",
        title="Origin locations",
    ).update_layout(
        height=430,
        yaxis={"categoryorder": "total ascending"},
        xaxis={"range": [0, 4000], "title": "Reported arrivals"},
        margin={"l": 8, "r": 8, "t": 50, "b": 8},
    )
    destination_chart = px.bar(
        destinations,
        x="New arrivals",
        y="Destination region",
        orientation="h",
        title="Destination regions",
    ).update_layout(
        height=430,
        yaxis={"categoryorder": "total ascending"},
        xaxis={"range": [0, 4000], "title": "Reported arrivals"},
        margin={"l": 8, "r": 8, "t": 50, "b": 8},
    )
    origin_col.plotly_chart(origin_chart, use_container_width=True)
    destination_col.plotly_chart(destination_chart, use_container_width=True)
    st.info(
        "These are separate marginal distributions: the report provides counts by origin "
        "and counts by destination, but the displayed tables do not identify individual "
        "origin-to-destination routes. Do not infer bilateral flows, net migration, or "
        "regional gains and losses by subtracting one table from the other."
    )

    st.divider()
    st.subheader("Countrywide baseline assessment — Round 3 (2024)")
    st.markdown(
        "**Assessment period:** 14 February – 19 September 2024  \n"
        "**Coverage:** 17 regions and 82 districts  \n"
        "**Assessment type:** area-based baseline assessment / mobility tracking  \n"
        "**Population groups:** IDPs, returnees and residents."
    )
    st.link_button(
        "Open official Round 3 baseline dataset",
        "https://dtm.iom.int/datasets/somalia-baseline-assessment-dataset-round-3-february-2024-september-2024",
    )
    st.link_button(
        "Open 2024 baseline assessment GIS dashboard",
        "https://dtm.iom.int/",
    )

    st.divider()
    st.subheader("Data integration status")
    st.warning(
        "District-level observations are not yet loaded into this application. "
        "The public DTM API documentation describes Admin 1 and Admin 2 outputs, but its "
        "current API v3 requires a developer account and subscription key. The older API "
        "versions are no longer maintained. This module therefore links to official public "
        "datasets rather than scraping unstable page content or presenting invented values."
    )
    st.markdown(
        "**Planned integration fields**  \n"
        "- Assessment round and reference date  \n"
        "- Region and district names / administrative codes  \n"
        "- Population group (IDP, returnee, resident)  \n"
        "- Population or new-arrival count, preserving the source's measure  \n"
        "- Displacement reason and settlement type, where published  \n"
        "- Assessment coverage and source citation"
    )
    st.caption(
        "Important: baseline population presence and weekly ETT new arrivals are different measures. "
        "They must be stored and visualized separately. New arrivals may include secondary or repeated "
        "displacement and should not automatically be treated as unique newly displaced persons."
    )
    st.markdown(
        "Sources: [IOM DTM Somalia ETT dataset](https://dtm.iom.int/datasets/somalia-emergency-trend-tracking-dataset-june-2026-0) · "
        "[IOM DTM Somalia baseline dataset](https://dtm.iom.int/datasets/somalia-baseline-assessment-dataset-round-3-february-2024-september-2024) · "
        "[DTM API documentation](https://dtm.iom.int/data-and-analysis/dtm-api)"
    )
    st.stop()

if analysis_view == "Somalia displacement profile":
    st.header("Somalia displacement intelligence profile")
    st.caption(
        "A country-focused view of population statistics reported through UNHCR's official "
        "PopStatsOfficial series. Hosting and origin dimensions are shown separately."
    )
    st.info(
        "Somalia as a hosting country measures people reported in Somalia. Somalia as a country "
        "of origin measures people reported as originating from Somalia. These are different "
        "dimensions and must not be added together."
    )

    with st.spinner("Retrieving Somalia's historical hosting and origin series..."):
        try:
            somalia_host_trend = country_trend(selected_type, "SOM", "ref_area_adm0")
        except UNHCRDataError as exc:
            st.warning(f"Somalia hosting series could not be retrieved: {exc}")
            somalia_host_trend = pd.DataFrame()
        try:
            somalia_origin_trend = country_trend(selected_type, "SOM", "area_ori_adm0")
        except UNHCRDataError as exc:
            st.warning(f"Somalia origin series could not be retrieved: {exc}")
            somalia_origin_trend = pd.DataFrame()

    left, right = st.columns(2)
    if not somalia_host_trend.empty:
        latest_host = somalia_host_trend.iloc[-1]
        left.metric("Somalia — hosting population", f"{latest_host['population']:,.0f}", help=f"Latest available period: {latest_host['time_period']}")
        host_fig = px.line(
            somalia_host_trend, x="time_period", y="population", markers=True,
            labels={"time_period": "Reporting period", "population": "People"},
            title="Population hosted in Somalia",
        )
        host_fig.update_layout(yaxis_tickformat=",", xaxis_tickangle=-45)
        left.plotly_chart(host_fig, use_container_width=True)
    else:
        left.info("No unambiguous historical hosting series was returned for Somalia and this category.")

    if not somalia_origin_trend.empty:
        latest_origin = somalia_origin_trend.iloc[-1]
        right.metric("Somalia — origin population", f"{latest_origin['population']:,.0f}", help=f"Latest available period: {latest_origin['time_period']}")
        origin_fig = px.line(
            somalia_origin_trend, x="time_period", y="population", markers=True,
            labels={"time_period": "Reporting period", "population": "People"},
            title="Population originating from Somalia",
        )
        origin_fig.update_layout(yaxis_tickformat=",", xaxis_tickangle=-45)
        right.plotly_chart(origin_fig, use_container_width=True)
    else:
        right.info("No unambiguous historical origin series was returned for Somalia and this category.")

    st.subheader("Somalia and neighbouring countries — hosting comparison")
    st.caption(
        f"Selected category: {type_labels.get(selected_type, selected_type)} · "
        f"Reporting period: {selected_period}. Comparison uses country-of-asylum totals only."
    )
    host_ranking = country_ranking(df, selected_type, "ref_area_adm0", selected_period, limit=300)
    neighbours = {"SOM": "Somalia", "ETH": "Ethiopia", "KEN": "Kenya", "DJI": "Djibouti", "YEM": "Yemen"}
    if host_ranking.empty:
        st.info("No unique hosting-country totals are available for the selected period.")
    else:
        host_ranking = host_ranking.copy()
        host_ranking["iso3"] = host_ranking["country"].map(country_iso3)
        regional = host_ranking[host_ranking["iso3"].isin(neighbours)].copy()
        regional["country"] = regional["iso3"].map(neighbours)
        regional = regional[["country", "iso3", "population"]].sort_values("population", ascending=False)
        if regional.empty:
            st.info("No comparable Somalia / neighbouring-country records were returned for this period.")
        else:
            st.dataframe(regional, hide_index=True, use_container_width=True)
            regional_fig = px.bar(
                regional.sort_values("population"),
                x="population", y="country", orientation="h",
                labels={"population": "People", "country": "Hosting country"},
                title="Reported hosting populations in the Horn of Africa and Yemen",
            )
            regional_fig.update_layout(xaxis_tickformat=",")
            st.plotly_chart(regional_fig, use_container_width=True)
            st.download_button(
                "Download regional comparison (CSV)",
                data=regional.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"somalia_neighbour_comparison_{selected_type}_{selected_period}.csv",
                mime="text/csv",
            )

    st.warning(
        "Interpretation limits: this page reports only the selected UNHCR population category. "
        "It does not combine refugee, asylum-seeker, IDP, returnee or other categories into one "
        "displacement total. Neighbouring-country comparisons are descriptive and do not establish "
        "causes, cross-border movements, or national vulnerability."
    )
    st.markdown(
        "Source: [UNHCR Population Statistics](https://refugeedata.unhcr.org/en/data-finder/detail/PopStatsOfficial/data/) · "
        "[UNHCR API documentation](https://refugeedata.unhcr.org/en/documentation/technical-reference/api/)"
    )
    st.stop()

if analysis_view == "Displacement pressure signals":
    st.header("Country displacement pressure signals")
    st.caption(
        "A descriptive screening view of recent country-level population-stock changes. "
        "It is not a predictive risk score and does not identify causes."
    )
    measure = population_measure_type(selected_type)
    if measure != "stock":
        st.warning("This analysis is limited to population stocks. Select a stock category; flow categories are not suitable for this comparison.")
        st.stop()
    if role == "Countries of origin":
        st.warning("This first release is limited to country-of-asylum / hosting totals to keep the geographic definition consistent.")
        st.stop()

    signals = country_pressure_signals(df, selected_type, "ref_area_adm0")
    if signals.empty:
        st.warning("Insufficient comparable observations were available, or duplicate country-period keys prevented a safe comparison.")
        st.stop()

    positive = signals[signals["absolute_change"] > 0]
    negative = signals[signals["absolute_change"] < 0]
    p1, p2, p3 = st.columns(3)
    p1.metric("Countries compared", f"{len(signals):,}")
    p2.metric("Countries with increases", f"{len(positive):,}")
    p3.metric("Countries with decreases", f"{len(negative):,}")
    st.caption(
        f"{selected_type} · Hosting-country totals · "
        f"{signals['previous_period'].iloc[0]} to {signals['latest_period'].iloc[0]}"
    )

    st.subheader("Largest absolute increases")
    if positive.empty:
        st.info("No increases were observed among comparable countries.")
    else:
        chart = px.bar(
            positive.head(15).sort_values("absolute_change"),
            x="absolute_change", y="country", orientation="h",
            labels={"absolute_change": "Change in people", "country": "Hosting country"},
        )
        st.plotly_chart(chart, use_container_width=True)

    st.subheader("Countries increasing across four observed periods")
    persistent = signals[signals["increasing_across_four_observed_periods"].eq(True)]
    st.caption("A country is flagged only when it has a non-missing observation in each of the latest four reporting periods and its value rises at every successive observed period. The periods are not assumed to be equally spaced.")
    if persistent.empty:
        st.info("No countries met this descriptive persistence condition, or four comparable periods were unavailable.")
    else:
        st.dataframe(persistent, hide_index=True, use_container_width=True)

    st.subheader("All comparable countries")
    st.dataframe(signals, hide_index=True, use_container_width=True)
    st.download_button(
        "Download displacement pressure signals (CSV)",
        data=signals.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"displacement_pressure_{selected_type}.csv",
        mime="text/csv",
    )
    st.info(
        "Method: compares only countries with valid observations in both latest shared reporting periods. "
        "Persistence requires four observed periods with strictly increasing values. Missing values are not zero; "
        "categories are not combined. These signals are descriptive and must not be interpreted as causal findings, "
        "future displacement forecasts, or a validated risk classification."
    )
    st.stop()

if analysis_view == "Historical change analysis":
    st.header("Historical country change analysis")
    st.caption(
        "Compares country-level totals between two observed reporting periods. "
        "Only countries with a valid observation in both periods are included."
    )
    if len(periods) < 2:
        st.info("At least two reporting periods are required for a change comparison.")
        st.stop()
    default_later = len(periods) - 1
    default_earlier = max(0, default_later - 1)
    p1, p2 = st.columns(2)
    earlier_period = p1.selectbox("Earlier reporting period", periods, index=default_earlier)
    later_period = p2.selectbox("Later reporting period", periods, index=default_later)
    if earlier_period == later_period:
        st.warning("Choose two different reporting periods.")
        st.stop()

    changes = country_period_changes(df, selected_type, "ref_area_adm0", earlier_period, later_period)
    if changes.empty:
        st.warning(
            "No comparable country totals were available for both periods, or duplicate "
            "dimension keys prevented a safe comparison."
        )
    else:
        increases = changes[changes["absolute_change"] > 0].sort_values("absolute_change", ascending=False)
        decreases = changes[changes["absolute_change"] < 0].sort_values("absolute_change")
        unchanged = int((changes["absolute_change"] == 0).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Countries compared", f"{len(changes):,}")
        m2.metric("Countries with increases", f"{len(increases):,}")
        m3.metric("Countries with decreases", f"{len(decreases):,}")
        st.caption(f"Population category: {type_labels.get(selected_type, selected_type)} · {earlier_period} to {later_period} · {unchanged} unchanged")
        if not increases.empty:
            st.subheader("Largest increases")
            increase_chart = px.bar(
                increases.head(15).sort_values("absolute_change"),
                x="absolute_change", y="country", orientation="h",
                labels={"absolute_change": "Absolute change (people)", "country": "Hosting country"},
            )
            st.plotly_chart(increase_chart, use_container_width=True)
            st.dataframe(increases, hide_index=True, use_container_width=True)
        if not decreases.empty:
            st.subheader("Largest decreases")
            decrease_chart = px.bar(
                decreases.head(15).sort_values("absolute_change"),
                x="absolute_change", y="country", orientation="h",
                labels={"absolute_change": "Absolute change (people)", "country": "Hosting country"},
            )
            st.plotly_chart(decrease_chart, use_container_width=True)
            st.dataframe(decreases, hide_index=True, use_container_width=True)
        st.subheader("All comparable countries")
        st.dataframe(changes, hide_index=True, use_container_width=True)
        export = changes.copy()
        export.insert(0, "later_period", later_period)
        export.insert(0, "earlier_period", earlier_period)
        export.insert(0, "population_category", selected_type)
        st.download_button(
            "Download country change analysis (CSV)",
            data=export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"country_changes_{selected_type}_{earlier_period}_{later_period}.csv",
            mime="text/csv",
        )
    st.info(
        "Method: absolute change = later-period population minus earlier-period population. "
        "Percentage change is calculated only where the earlier value is non-zero. "
        "Countries missing either period are excluded, not assigned zero. Results are "
        "descriptive comparisons, not causal explanations or forecasts. For flow-related "
        "categories, changes should not be interpreted as changes in a population stock."
    )
    st.stop()

if analysis_view == "Global hosting map":
    st.header("Global refugee hosting map")
    st.caption(
        f"Geographical distribution for {selected_period} · "
        f"{type_labels.get(selected_type, selected_type)}"
    )
    if ranking.empty:
        st.warning("No unambiguous country totals are available for this selection.")
    else:
        map_data = ranking.copy()
        map_data["iso3"] = map_data["country"].map(country_iso3)
        mapped = map_data[map_data["iso3"].notna()].copy()
        unmapped = map_data[map_data["iso3"].isna()].copy()

        if not mapped.empty:
            map_fig = px.choropleth(
                mapped,
                locations="iso3",
                locationmode="ISO-3",
                color="population",
                hover_name="country",
                hover_data={"population": ":,", "iso3": False},
                color_continuous_scale="Blues",
                labels={"population": "People"},
                title="Reported refugee population by hosting country",
            )
            map_fig.update_geos(
                showframe=False,
                showcoastlines=True,
                projection_type="natural earth",
            )
            map_fig.update_layout(
                height=650,
                margin={"r": 0, "t": 55, "l": 0, "b": 0},
            )
            st.plotly_chart(map_fig, use_container_width=True)
        else:
            st.error("No country labels could be matched to ISO-3 codes; the map was not rendered.")

        st.caption(
            f"Mapped {len(mapped):,} of {len(map_data):,} country records "
            f"({len(mapped) / len(map_data) * 100:.1f}% coverage)."
        )
        if not unmapped.empty:
            st.warning(
                f"{len(unmapped):,} country label(s) could not be matched to an ISO-3 code. "
                "They are retained below and are not silently discarded."
            )
            st.dataframe(unmapped[["country", "population"]], hide_index=True, use_container_width=True)

        st.subheader("Country totals")
        st.dataframe(ranking, hide_index=True, use_container_width=True)
        map_export = map_data.copy()
        map_export.insert(0, "reporting_period", selected_period)
        map_export.insert(0, "population_category", selected_type)
        st.download_button(
            "Download map data (CSV)",
            data=map_export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"global_hosting_map_{selected_type}_{selected_period}.csv",
            mime="text/csv",
        )
    st.info(
        "The map uses ISO-3 geographic identifiers. Country labels without a verified "
        "ISO-3 match remain in the accompanying table and are listed separately; "
        "they are not treated as zero or silently removed."
    )
    st.stop()

if analysis_view == "Global hosting comparison":
    st.header("Global hosting countries comparison")
    st.caption(
        f"Country totals for {selected_period} · "
        f"{type_labels.get(selected_type, selected_type)}"
    )
    if ranking.empty:
        st.warning(
            "No unambiguous country totals are available for this selection. "
            "The dashboard does not sum overlapping records."
        )
    else:
        top_country = ranking.iloc[0]
        left, middle, right = st.columns(3)
        left.metric("Countries with reported totals", f"{len(ranking):,}")
        middle.metric("Largest hosting country", str(top_country["country"]))
        right.metric("Largest hosting-country population", f"{top_country['population']:,.0f}")

        st.subheader("Top 20 refugee-hosting countries")
        top20 = ranking.head(20).sort_values("population")
        comparison_fig = px.bar(
            top20,
            x="population",
            y="country",
            orientation="h",
            labels={"population": "People", "country": "Hosting country"},
            title="Top 20 hosting countries",
        )
        comparison_fig.update_layout(height=650, yaxis_title=None)
        st.plotly_chart(comparison_fig, use_container_width=True)

        st.subheader("Complete country ranking")
        st.caption(
            f"Showing all {len(ranking):,} countries with an unambiguous reported total. "
            "The sum of country totals is not presented as an official global total."
        )
        st.dataframe(ranking, hide_index=True, use_container_width=True)
        comparison_export = ranking.copy()
        comparison_export.insert(0, "reporting_period", selected_period)
        comparison_export.insert(0, "population_category", selected_type)
        st.download_button(
            "Download global hosting comparison (CSV)",
            data=comparison_export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"global_hosting_comparison_{selected_type}_{selected_period}.csv",
            mime="text/csv",
        )
    st.info(
        "These are country-level hosting totals, not a sum across origin countries. "
        "Do not add population categories together or interpret missing observations as zero."
    )
    st.stop()

st.subheader("Country ranking — " + role)

if ranking.empty:
    st.warning("No unambiguous country totals are available for this selection. The dashboard does not sum overlapping records.")
else:
    fig = px.bar(
        ranking.sort_values("population"),
        x="population",
        y="country",
        orientation="h",
        labels={"population": "People", "country": "Country"},
    )
    fig.update_layout(height=max(420, 25 * len(ranking)), yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ranking, hide_index=True, use_container_width=True)

    st.subheader("Historical country trend")
    chosen = st.selectbox("Choose a country", ranking["country"].tolist())
    label_col = geo + "_label"
    candidates = df[[geo] + ([label_col] if label_col in df.columns else [])].dropna().drop_duplicates()
    if label_col in candidates.columns:
        found = candidates[candidates[label_col].astype(str).eq(chosen)]
    else:
        found = candidates[candidates[geo].astype(str).eq(chosen)]
    if not found.empty:
        selected_geo_code = str(found.iloc[0][geo])

        if geo == "ref_area_adm0":
            st.subheader(f"Countries of origin among people hosted in {chosen}")
            with st.spinner("Retrieving country-of-origin breakdown..."):
                try:
                    origins = country_origin_breakdown(selected_type, selected_geo_code, selected_period)
                except UNHCRDataError as exc:
                    st.warning(f"Origin breakdown could not be retrieved: {exc}")
                    origins = pd.DataFrame()

            if not origins.empty:
                # Use the selected hosting-country headline total from the same
                # population type and reporting period as the origin breakdown.
                host_rows = ranking[
                    ranking["country"].astype(str).eq(chosen)
                ]["population"].dropna()
                host_total = float(host_rows.iloc[0]) if len(host_rows) == 1 else None
                origins = origins.copy()
                origin_sum = float(origins["population"].sum())

                if host_total is not None and host_total > 0:
                    origins["share_of_host_total_pct"] = (
                        origins["population"] / host_total * 100
                    )
                    coverage_pct = origin_sum / host_total * 100
                    x, y, z = st.columns(3)
                    x.metric("Hosting-country total", f"{host_total:,.0f}")
                    y.metric("Origin records retrieved", f"{origin_sum:,.0f}")
                    z.metric("Origin coverage", f"{coverage_pct:.1f}%")

                    if origin_sum <= host_total:
                        unallocated = host_total - origin_sum
                        st.caption(
                            f"{unallocated:,.0f} people ({100 - coverage_pct:.1f}%) "
                            "are not represented in the listed origin-country records. "
                            "This may include unspecified origin or other unreturned categories; "
                            "it is not assigned to a country."
                        )
                    else:
                        st.warning(
                            "The sum of origin-country records exceeds the hosting-country total. "
                            "Do not interpret the percentages as reconciled until the API dimensions "
                            "and source records have been investigated."
                        )
                else:
                    st.warning(
                        "A unique hosting-country total was not available for this selection. "
                        "Origin shares and reconciliation are therefore not calculated."
                    )

                origin_fig = px.bar(
                    origins.head(15).sort_values("population"),
                    x="population",
                    y="country_of_origin",
                    orientation="h",
                    labels={"population": "People", "country_of_origin": "Country of origin"},
                    hover_data={"share_of_host_total_pct": ":.1f%"} if "share_of_host_total_pct" in origins.columns else None,
                )
                origin_fig.update_layout(height=max(380, 25 * min(len(origins), 15)), yaxis_title=None)
                st.plotly_chart(origin_fig, use_container_width=True)
                display_cols = ["country_of_origin", "population"]
                if "share_of_host_total_pct" in origins.columns:
                    display_cols.append("share_of_host_total_pct")
                st.dataframe(origins[display_cols], hide_index=True, use_container_width=True)

                # Portable, source-labelled country profile data export.
                export = origins[display_cols].copy()
                export.insert(0, "reporting_period", selected_period)
                export.insert(0, "population_category", selected_type)
                export.insert(0, "hosting_country", chosen)
                export["hosting_country_total"] = host_total
                export["origin_records_total"] = origin_sum
                export["origin_coverage_pct"] = (
                    origin_sum / host_total * 100 if host_total else None
                )
                st.download_button(
                    "Download country profile data (CSV)",
                    data=export.to_csv(index=False).encode("utf-8-sig"),
                    file_name=(
                        f"{selected_geo_code}_{selected_type}_{selected_period}_"
                        "country_profile.csv"
                    ),
                    mime="text/csv",
                    help="Exports the displayed origin-country records with population category, "
                         "hosting country, reporting period, total and coverage metadata.",
                )
            else:
                st.info(
                    "No unambiguous country-of-origin records were returned for this hosting country "
                    "and reporting period. The dashboard does not estimate or sum missing categories."
                )

        with st.spinner("Retrieving the selected country's historical series..."):
            try:
                trend = country_trend(selected_type, selected_geo_code, geo)
            except UNHCRDataError as exc:
                st.warning(f"Historical series could not be retrieved: {exc}")
                trend = pd.DataFrame()
        if not trend.empty:
            chart = px.line(
                trend,
                x="time_period",
                y="population",
                markers=True,
                labels={"time_period": "Period", "population": "People"},
            )
            chart.update_layout(yaxis_tickformat=",")
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("An unambiguous historical time series is not available for this country.")

with st.expander("Data notes and interpretation"):
    st.markdown(
        "- Source: UNHCR Refugee Data Portal, PopStatsOfficial.\n"
        "- The app queries the latest available reporting-year slice for the selected population type.\n"
        "- Population stocks must not be summed across years. Some solution-related series are flows.\n"
        "- Country of asylum and country of origin are separate views and may overlap.\n"
        "- The API's default dimensions provide headline totals; the dashboard does not add demographic breakdowns.\n"
        "- Missing observations are not zero.\n"
        "- Global totals are displayed only when an explicit unambiguous total row is present."
    )
    st.markdown(
        "[UNHCR API documentation](https://refugeedata.unhcr.org/en/documentation/technical-reference/api/) · "
        "[Official population statistics](https://refugeedata.unhcr.org/en/data-finder/detail/PopStatsOfficial/data/)"
    )

st.caption("Research dashboard · initial implementation")
