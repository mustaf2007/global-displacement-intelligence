from io import BytesIO
import pandas as pd
import requests
import streamlit as st

BASE_URL = 'https://api-data.unhcr.org/api/v0'
SERIES = 'PopStatsOfficial'
CSV_URL = f'{BASE_URL}/data/export/{SERIES}'

class UNHCRDataError(RuntimeError):
    pass

@st.cache_data(ttl=86400, show_spinner=False)
def load_population_data():
    try:
        response = requests.get(CSV_URL, timeout=(15, 180), headers={'User-Agent': 'Global-Displacement-Intelligence/0.1'})
        response.raise_for_status()
        if not response.content:
            raise UNHCRDataError('UNHCR returned an empty CSV.')
        frame = pd.read_csv(BytesIO(response.content), low_memory=False)
    except (requests.RequestException, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise UNHCRDataError(f'Unable to retrieve or parse UNHCR data: {exc}') from exc
    required = {'time_period', 'pop_type', 'obs_value'}
    missing = required.difference(frame.columns)
    if missing:
        raise UNHCRDataError('UNHCR schema changed; missing columns: ' + ', '.join(sorted(missing)))
    frame = frame.copy()
    frame['time_period'] = frame['time_period'].astype('string').str.strip()
    frame['pop_type'] = frame['pop_type'].astype('string').str.strip()
    frame['obs_value'] = pd.to_numeric(frame['obs_value'], errors='coerce')
    return frame.drop_duplicates()

def latest_period(frame):
    periods = frame['time_period'].dropna().astype(str)
    return max(periods) if not periods.empty else None

def headline_rows(frame):
    out = frame.copy()
    for dim in ('sex', 'age', 'urbanisation', 'setting'):
        if dim in out.columns:
            out = out[out[dim].astype('string').eq('_T')]
    return out

def population_types(frame):
    cols = ['pop_type'] + (['pop_type_label'] if 'pop_type_label' in frame.columns else [])
    return frame[cols].dropna(subset=['pop_type']).drop_duplicates().sort_values(cols).reset_index(drop=True)

def explicit_global_total(frame, pop_type, period):
    data = headline_rows(frame[frame['pop_type'].astype('string').eq(pop_type)].copy())
    geo = [c for c in ('ref_area_adm0', 'area_ori_adm0') if c in data.columns]
    if not geo:
        return None
    mask = data[geo[0]].astype('string').eq('_T')
    for col in geo[1:]:
        mask = mask | data[col].astype('string').eq('_T')
    values = data.loc[mask & data['time_period'].astype('string').eq(period), 'obs_value'].dropna().drop_duplicates()
    return values.iloc[0] if len(values) == 1 else None

def country_ranking(frame, pop_type, geography, period, limit=20):
    if geography not in ('ref_area_adm0', 'area_ori_adm0') or geography not in frame.columns:
        return pd.DataFrame(columns=['country', 'population'])
    data = frame[frame['pop_type'].astype('string').eq(pop_type) & frame['time_period'].astype('string').eq(period)].copy()
    data = headline_rows(data)
    data = data[data[geography].notna() & ~data[geography].astype('string').isin(['_T', '_X'])]
    opposite = 'area_ori_adm0' if geography == 'ref_area_adm0' else 'ref_area_adm0'
    if opposite in data.columns:
        data = data[data[opposite].astype('string').eq('_T')]
    label = geography + '_label'
    name_col = label if label in data.columns else geography
    data = data[[geography, name_col, 'obs_value']].dropna(subset=['obs_value']).drop_duplicates()
    data = data[~data[geography].duplicated(keep=False)]
    return data[[name_col, 'obs_value']].rename(columns={name_col:'country', 'obs_value':'population'}).sort_values('population', ascending=False).head(limit).reset_index(drop=True)

def country_trend(frame, pop_type, geo_code, geography):
    data = frame[frame['pop_type'].astype('string').eq(pop_type) & frame[geography].astype('string').eq(geo_code)].copy()
    data = headline_rows(data)
    opposite = 'area_ori_adm0' if geography == 'ref_area_adm0' else 'ref_area_adm0'
    if opposite in data.columns:
        data = data[data[opposite].astype('string').eq('_T')]
    data = data[~data['time_period'].duplicated(keep=False)]
    return data[['time_period','obs_value']].dropna(subset=['obs_value']).rename(columns={'obs_value':'population'}).sort_values('time_period').reset_index(drop=True)
