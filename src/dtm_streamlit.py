from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dtm_api import DTMConnectorError, build_dtm_client, fetch_idp_data
from src.dtm_advanced_quality import advanced_idp_quality_report
from src.dtm_explorer import explorer_coverage_summary, filter_idp_snapshot
from src.dtm_quality import profile_idp_data


def validate_reporting_date_filters(from_date: str = '', to_date: str = '') -> tuple[str | None, str | None]:
    """Validate optional ISO reporting-date filters and return normalized dates."""
    normalized = []
    for label, value in [('From reporting date', from_date), ('To reporting date', to_date)]:
        value = value.strip() if isinstance(value, str) else ''
        if not value:
            normalized.append(None)
            continue
        parsed = pd.to_datetime(value, format='%Y-%m-%d', errors='coerce')
        if pd.isna(parsed) or parsed.strftime('%Y-%m-%d') != value:
            raise ValueError(f'{label} must use a valid YYYY-MM-DD date.')
        normalized.append(parsed.strftime('%Y-%m-%d'))
    start, end = normalized
    if start and end and pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError('The start date must be on or before the end date.')
    return start, end


def _configured_key() -> str | None:
    key = os.getenv('DTMAPI_SUBSCRIPTION_KEY')
    if key:
        return key
    try:
        value = st.secrets.get('DTMAPI_SUBSCRIPTION_KEY')
        return str(value) if value else None
    except Exception:
        return None


def render_dtm_explorer() -> None:
    st.header('IOM DTM IDP assessment explorer')
    st.caption('Explore official DTM API v3 IDP population assessment snapshots by administrative level and reporting date.')
    st.info('This module retrieves IDP population-stock assessment records. It is not the Somalia Emergency Trend Tracking (ETT) weekly-arrivals dataset and must not be interpreted as a movement-flow dashboard.')

    key = _configured_key()
    if not key:
        st.warning('DTM API access is not configured.')
        st.markdown('To enable this page, register for API-V3 at the [IOM DTM Developer Portal](https://dtm-apim-portal.iom.int/) and add DTMAPI_SUBSCRIPTION_KEY to deployment secrets or the server environment. Do not place the key in source code.')
        st.stop()

    left, middle, right = st.columns(3)
    with left:
        admin_label = st.selectbox('Administrative level', ['Regional (Admin 1)', 'District (Admin 2)', 'Country (Admin 0)'])
    admin_level = {'Country (Admin 0)': 0, 'Regional (Admin 1)': 1, 'District (Admin 2)': 2}[admin_label]
    with middle:
        from_input = st.text_input('From reporting date (optional)', placeholder='YYYY-MM-DD')
    with right:
        to_input = st.text_input('To reporting date (optional)', placeholder='YYYY-MM-DD')

    try:
        from_date, to_date = validate_reporting_date_filters(from_input, to_input)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if not st.button('Retrieve DTM assessment data', type='primary'):
        st.caption('No API request is made until you select the retrieval button. The page does not cache or persist returned records.')
        st.stop()

    try:
        client = build_dtm_client(subscription_key=key)
        with st.spinner('Requesting DTM API v3 assessment records...'):
            raw = fetch_idp_data(country_name='Somalia', admin_level=admin_level, from_reporting_date=from_date, to_reporting_date=to_date, client=client)
    except (DTMConnectorError, ValueError) as exc:
        st.error(f'DTM data could not be retrieved: {exc}')
        st.stop()

    if raw.empty:
        st.warning('The API returned no records for this query. This does not establish that the population is zero or that geographic coverage is complete.')
        st.stop()
    try:
        summary = explorer_coverage_summary(raw, admin_level)
        quality = profile_idp_data(raw, admin_level)
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f'The returned data could not be profiled safely: {exc}')
        st.stop()

    st.subheader('Returned data coverage')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Records returned', f"{summary['rows_returned']:,}")
    c2.metric('Geographic units', f"{summary['geographic_units_returned']:,}")
    c3.metric('First reporting date', summary['earliest_reporting_date'] or 'Unavailable')
    c4.metric('Latest reporting date', summary['latest_reporting_date'] or 'Unavailable')
    if quality['status'] == 'passed_basic_checks':
        st.success('Returned records passed the basic structural checks.')
    else:
        st.warning(f"Data quality status: {quality['status']}. Review diagnostics before interpreting or publishing.")

    geo_field = {0: 'admin0Name', 1: 'admin1Name', 2: 'admin2Name'}[admin_level]
    selected_admin1 = None
    if admin_level == 2 and 'admin1Name' in raw.columns:
        options = sorted(raw['admin1Name'].dropna().astype(str).unique())
        choice = st.selectbox('Filter by region', ['All returned regions'] + options)
        selected_admin1 = None if choice == 'All returned regions' else choice
    selected_admin2 = None
    if admin_level == 2 and 'admin2Name' in raw.columns:
        options = sorted(raw['admin2Name'].dropna().astype(str).unique())
        choice = st.selectbox('Filter by district', ['All returned districts'] + options)
        selected_admin2 = None if choice == 'All returned districts' else choice
    try:
        displayed = filter_idp_snapshot(raw, admin_level, admin1=selected_admin1, admin2=selected_admin2, from_date=from_date, to_date=to_date)
    except (TypeError, ValueError) as exc:
        st.error(f'Filters could not be applied: {exc}')
        st.stop()

    if displayed.empty:
        st.info('No records match the selected filters. Missing observations are not treated as zero.')
    else:
        st.subheader('Assessment observations')
        st.caption(f'Showing {len(displayed):,} source records. Values are displayed as returned; records are not summed across assessment rounds.')
        st.dataframe(displayed, hide_index=True, use_container_width=True)
        numeric = pd.to_numeric(displayed['numPresentIdpInd'], errors='coerce')
        chart_data = displayed.loc[numeric.notna(), [geo_field, 'reportingDate']].copy()
        chart_data['reported_idp_individuals'] = numeric.loc[numeric.notna()].values
        chart_data['reportingDate'] = pd.to_datetime(chart_data['reportingDate'], errors='coerce')
        chart_data = chart_data.dropna(subset=['reportingDate'])
        if not chart_data.empty:
            chart = px.scatter(chart_data, x='reportingDate', y='reported_idp_individuals', color=geo_field, hover_data=[geo_field], labels={'reportingDate': 'Reporting date', 'reported_idp_individuals': 'Reported IDP individuals', geo_field: 'Administrative unit'}, title='Reported IDP assessment observations by date')
            chart.update_layout(height=520)
            st.plotly_chart(chart, use_container_width=True)
        st.download_button('Download filtered observations (CSV)', data=displayed.to_csv(index=False).encode('utf-8-sig'), file_name=f'iom_dtm_somalia_admin{admin_level}_observations.csv', mime='text/csv')

    advanced = advanced_idp_quality_report(raw, admin_level)
    with st.expander('Data quality and geographic coverage details'):
        st.write('Basic structural diagnostics', quality)
        st.caption(summary['coverage_interpretation'])
        st.write('Returned geographic units', summary['geographic_units'])
        st.markdown('**Second-stage validation**')
        g1, g2, g3 = st.columns(3)
        g1.metric('Unique reporting dates', advanced['temporal']['unique_reporting_dates'])
        g2.metric('Units with returned records', advanced['geography']['unique_names'])
        g3.metric('Latest reporting date', advanced['temporal']['latest_reporting_date'] or 'Unavailable')
        st.write('Geographic code consistency', advanced['geography'])
        if advanced['parent_geography']['available']:
            st.write('Parent-region consistency', advanced['parent_geography'])
        st.markdown('**Reporting-date coverage by returned geographic unit**')
        coverage = pd.DataFrame(advanced['unit_reporting_coverage'])
        if not coverage.empty:
            st.dataframe(coverage, hide_index=True, use_container_width=True)
        st.markdown('**Demographic and origin-field missingness**')
        missingness = pd.DataFrame(advanced['demographic_missingness'])
        if not missingness.empty:
            st.dataframe(missingness, hide_index=True, use_container_width=True)
        st.markdown('**Assessment provenance breakdown**')
        for field, rows in advanced['provenance_breakdown'].items():
            st.write(field, pd.DataFrame(rows))
        st.caption(advanced['interpretation'])
        st.caption('These checks describe returned records only. They do not independently validate source assessments or establish complete national coverage.')
    st.markdown('**Source:** [IOM Displacement Tracking Matrix](https://dtm.iom.int/) · [DTM API documentation](https://dtm.iom.int/data-and-analysis/dtm-api)')
