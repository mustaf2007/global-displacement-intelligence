import pandas as pd
import plotly.express as px
import streamlit as st

from src.unhcr import (
    UNHCRDataError,
    country_ranking,
    country_trend,
    explicit_global_total,
    latest_period,
    load_population_data,
    country_origin_breakdown,
    population_types,
)

st.set_page_config(page_title="Global Refugee & Displacement Intelligence", page_icon="🌍", layout="wide")
st.title("🌍 Global Refugee & Displacement Intelligence")
st.caption("Official population statistics from the UNHCR Refugee Data Portal")

type_labels = {
    "REF_UNHCR": "Refugees under UNHCR's mandate",
    "REF_UNRWA": "Palestine refugees under UNRWA's mandate",
    "ASY": "Asylum-seekers",
    "OIP": "Other people in need of international protection",
    "IDP": "Internally displaced people",
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
geo = "ref_area_adm0" if role == "Countries of asylum / hosting" else "area_ori_adm0"

global_total = explicit_global_total(df, selected_type, selected_period)
a, b, c = st.columns(3)
a.metric("Explicit global total", f"{global_total:,.0f}" if global_total is not None else "Not supplied")
b.metric("Selected period", selected_period)
c.metric("Records retrieved", f"{len(df):,}")

st.caption(f"Latest reporting period in the retrieved slice: {latest_period(df) or 'Unknown'}")
st.divider()
ranking = country_ranking(df, selected_type, geo, selected_period)
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
                origin_fig = px.bar(
                    origins.head(15).sort_values("population"),
                    x="population",
                    y="country_of_origin",
                    orientation="h",
                    labels={"population": "People", "country_of_origin": "Country of origin"},
                )
                origin_fig.update_layout(height=max(380, 25 * min(len(origins), 15)), yaxis_title=None)
                st.plotly_chart(origin_fig, use_container_width=True)
                st.dataframe(origins, hide_index=True, use_container_width=True)
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
