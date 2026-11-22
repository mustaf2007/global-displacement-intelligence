import pandas as pd
import plotly.express as px
import streamlit as st
from src.unhcr import UNHCRDataError, load_population_data, latest_period, population_types, explicit_global_total, country_ranking, country_trend

st.set_page_config(page_title='Global Displacement Intelligence', page_icon='🌍', layout='wide')
st.title('🌍 Global Refugee & Displacement Intelligence')
st.caption('Official population statistics from the UNHCR Refugee Data Portal')
try:
    with st.spinner('Downloading official UNHCR population statistics...'):
        df = load_population_data()
except UNHCRDataError as exc:
    st.error(str(exc))
    st.info('The public UNHCR endpoint must be reachable. No API key or account is required.')
    st.link_button('UNHCR API documentation', 'https://refugeedata.unhcr.org/en/documentation/technical-reference/api/')
    st.stop()
except Exception as exc:
    st.error(f'Data loading failed: {exc}')
    st.stop()
periods = sorted(df.time_period.dropna().astype(str).unique())
types = population_types(df)
if not periods or types.empty:
    st.error('No valid periods or population types were found in the source data.')
    st.stop()
codes = types.pop_type.astype(str).tolist()
label_col = 'pop_type_label' if 'pop_type_label' in types.columns else None
labels = {str(row.pop_type): str(getattr(row, label_col)) if label_col and pd.notna(getattr(row, label_col)) else str(row.pop_type) for _, row in types.iterrows()}
default = 'REF_UNHCR' if 'REF_UNHCR' in codes else codes[0]
with st.sidebar:
    st.header('Filters')
    selected_type = st.selectbox('Population category', codes, index=codes.index(default), format_func=lambda x: labels.get(x, x))
    selected_period = st.selectbox('Reporting period', periods, index=len(periods)-1)
    role = st.radio('Country view', ['Countries of asylum / hosting', 'Countries of origin'])
geo = 'ref_area_adm0' if role == 'Countries of asylum / hosting' else 'area_ori_adm0'
global_total = explicit_global_total(df, selected_type, selected_period)
a,b,c = st.columns(3)
a.metric('Explicit global total', f'{global_total:,.0f}' if global_total is not None else 'Not supplied')
b.metric('Selected period', selected_period)
c.metric('Source rows', f'{len(df):,}')
st.caption(f'Latest reporting period present in source: {latest_period(df) or "Unknown"}')
st.divider()
ranking = country_ranking(df, selected_type, geo, selected_period)
st.subheader('Country ranking — ' + role)
if ranking.empty:
    st.warning('No unambiguous country totals are available. The dashboard does not sum overlapping records.')
else:
    fig = px.bar(ranking.sort_values('population'), x='population', y='country', orientation='h', labels={'population':'People','country':'Country'})
    fig.update_layout(height=max(420, 25*len(ranking)), yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ranking, hide_index=True, use_container_width=True)
    st.subheader('Historical country trend')
    chosen = st.selectbox('Choose a country', ranking.country.tolist())
    label = geo + '_label'
    candidates = df[[geo] + ([label] if label in df.columns else [])].dropna().drop_duplicates()
    if label in candidates.columns:
        found = candidates[candidates[label].astype(str).eq(chosen)]
    else:
        found = candidates[candidates[geo].astype(str).eq(chosen)]
    if not found.empty:
        trend = country_trend(df, selected_type, str(found.iloc[0][geo]), geo)
        if not trend.empty:
            chart = px.line(trend, x='time_period', y='population', markers=True, labels={'time_period':'Period','population':'People'})
            chart.update_layout(yaxis_tickformat=',')
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info('An unambiguous time series is not available for this country.')
with st.expander('Data notes and interpretation'):
    st.markdown('- Source: UNHCR Refugee Data Portal, PopStatsOfficial.\n- Population values are stocks; do not sum across years.\n- Country of asylum and country of origin are different views and may overlap.\n- Sex, age, urbanisation and setting totals are not added together; explicit `_T` totals are used.\n- Missing observations are not zero.\n- Global totals are shown only when UNHCR explicitly supplies an unambiguous global row.')
    st.markdown('[UNHCR API documentation](https://refugeedata.unhcr.org/en/documentation/technical-reference/api/) · [Official data series](https://refugeedata.unhcr.org/en/data-finder/detail/PopStatsOfficial/data/)')
st.caption('Research dashboard · initial implementation')