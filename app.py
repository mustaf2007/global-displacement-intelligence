import pandas as pd
import plotly.express as px
import pycountry
import streamlit as st
from src.geo import country_iso3
from src.quality import audit_population_data, reconciliation_by_period
from src.unhcr import (
    UNHCRDataError,
    country_ranking,
    country_trend,
    explicit_global_total,
    latest_period,
    load_population_data,
    country_origin_breakdown,
    population_types,
    population_period_coverage,
)

st.set_page_config(page_title="Global Refugee & Displacement Intelligence", page_icon="🌍", layout="wide")
st.title("🌍 Global Refugee & Displacement Intelligence")
st.caption("Official population statistics from the UNHCR Refugee Data Portal")

type_labels = {
    "REF_UNHCR": "Refugees under UNHCR's mandate",
    "REF_UNRWA": "Palestine refugees under UNRWA's mandate",
    "ASY": "Asylum-seekers",
    "OIP": "Other people in need of international protection",
    "IDP_UNHCR": "Internally displaced people protected/assisted by UNHCR",
    "IDP_IDMC": "Internally displaced people (IDMC data)",
    "STA": "Stateless people",
}

with st.sidebar:
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
        ["Country explorer", "Global hosting comparison", "Global hosting map"],
        help="Compare country totals across all available hosting countries.",
    )

with st.spinner("Retrieving the latest UNHCR reporting period for the selected population category..."):
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

periods = sorted(df["time_period"].dropna().astype(str).unique())
if not periods:
    st.error("UNHCR returned no reporting periods for this population category.")
    st.stop()

selected_period = st.selectbox("Reporting period", periods, index=len(periods) - 1)
geo = (
    "ref_area_adm0"
    if analysis_view in ("Global hosting comparison", "Global hosting map") or role == "Countries of asylum / hosting"
    else "area_ori_adm0"
)

global_total = explicit_global_total(df, selected_type, selected_period)
a, b, c = st.columns(3)
a.metric("Explicit global total", f"{global_total:,.0f}" if global_total is not None else "Not supplied")
b.metric("Selected period", selected_period)
c.metric("Records retrieved", f"{len(df):,}")

st.caption(f"Latest reporting period in the retrieved slice: {latest_period(df) or 'Unknown'}")

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
