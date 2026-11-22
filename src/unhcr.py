from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://api-data.unhcr.org/api/v0"
DATA_URL = f"{BASE_URL}/data/PopStatsOfficial"
PAGE_SIZE = 100
HEADERS = {"User-Agent": "Global-Displacement-Intelligence/0.2"}

class UNHCRDataError(RuntimeError):
    """Raised when the UNHCR API cannot provide usable data."""


def _request_page(params: dict[str, Any]) -> dict[str, Any]:
    """Request one page, respecting UNHCR rate-limit responses."""
    for attempt in range(4):
        try:
            response = requests.get(DATA_URL, params=params, headers=HEADERS, timeout=(10, 45))
            if response.status_code == 429:
                time.sleep(min(5 * (attempt + 1), 20))
                continue
            if response.status_code in (502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                raise UNHCRDataError(f"UNHCR data query failed: {exc}") from exc
            time.sleep(2 * (attempt + 1))
            continue

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise UNHCRDataError("UNHCR returned an unexpected JSON response. Check the API schema.")
        return payload

    raise UNHCRDataError("UNHCR API rate limit or temporary service error. Please try again shortly.")


def _fetch_all(params: dict[str, Any], max_pages: int = 200) -> pd.DataFrame:
    """Walk API pages sequentially; never silently treat a partial result as complete."""
    rows: list[dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        query = dict(params)
        query.update({"page": page, "page_size": PAGE_SIZE})
        payload = _request_page(query)
        rows.extend(payload["data"])
        pagination = payload.get("pagination") or {}
        if not pagination.get("has_next", False):
            return pd.DataFrame(rows)
        page += 1
        time.sleep(1)  # UNHCR recommends no more than one query per second.

    raise UNHCRDataError(
        f"The UNHCR query exceeded the safety limit of {max_pages} pages. "
        "Narrow the query rather than displaying an incomplete dataset."
    )


@st.cache_data(ttl=86400, show_spinner=False)
def load_population_data(pop_type: str = "REF_UNHCR") -> pd.DataFrame:
    """Load all available reporting periods from 1960 onward for one population type."""
    params = {
        "c[pop_type]": pop_type,
        "time_period": "ge:1960",
        "dimensions": "default",
        "sort": "time_period:desc",
    }
    frame = _fetch_all(params)
    if frame.empty:
        raise UNHCRDataError(f"No records were returned for {pop_type} from 1960 onward.")
    required = {"time_period", "pop_type", "obs_value"}
    missing = required.difference(frame.columns)
    if missing:
        raise UNHCRDataError("UNHCR response is missing required fields: " + ", ".join(sorted(missing)))
    frame["obs_value"] = pd.to_numeric(frame["obs_value"], errors="coerce")
    frame["time_period"] = frame["time_period"].astype("string")
    return frame.drop_duplicates()



def filter_reporting_periods(
    frame: pd.DataFrame,
    start_period: str,
    end_period: str,
) -> pd.DataFrame:
    """Return records within an inclusive reporting-period range."""
    if "time_period" not in frame.columns:
        return frame.iloc[0:0].copy()
    start, end = str(start_period), str(end_period)
    if start > end:
        raise ValueError("The start reporting period must not be later than the end period.")
    periods = frame["time_period"].astype("string")
    mask = periods.notna() & periods.ge(start) & periods.le(end)
    return frame.loc[mask].copy()


def latest_period(frame: pd.DataFrame) -> str | None:
    periods = frame["time_period"].dropna().astype(str)
    return max(periods) if not periods.empty else None


def population_types() -> list[str]:
    """Common population-type codes in UNHCR's official population series."""
    return ["REF_UNHCR", "REF_UNRWA", "ASY", "OIP", "IDP_UNHCR", "IDP_IDMC", "RET", "RDP", "NAT", "RASP", "STA"]


def explicit_global_total(frame: pd.DataFrame, pop_type: str, period: str) -> float | None:
    data = frame[
        frame["pop_type"].astype("string").eq(pop_type)
        & frame["time_period"].astype("string").eq(period)
    ].copy()
    geo_cols = [c for c in ("ref_area_adm0", "area_ori_adm0") if c in data.columns]
    if not geo_cols:
        return None
    mask = pd.Series(True, index=data.index)
    for col in geo_cols:
        mask &= data[col].astype("string").isin(["_T", "<NA>", "nan"])
    values = data.loc[mask, "obs_value"].dropna().drop_duplicates()
    return float(values.iloc[0]) if len(values) == 1 else None


def country_ranking(frame: pd.DataFrame, pop_type: str, geography: str, period: str, limit: int = 20) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["country", "population"])
    if geography not in ("ref_area_adm0", "area_ori_adm0") or geography not in frame.columns:
        return empty
    data = frame[
        frame["pop_type"].astype("string").eq(pop_type)
        & frame["time_period"].astype("string").eq(period)
    ].copy()
    data = data[data[geography].notna() & ~data[geography].astype("string").isin(["_T", "_X"])]
    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    if opposite in data.columns:
        data = data[data[opposite].astype("string").eq("_T")]
    label = geography + "_label"
    name_col = label if label in data.columns else geography
    if name_col not in data.columns:
        return empty
    data = data[[geography, name_col, "obs_value"]].dropna(subset=["obs_value"]).drop_duplicates()
    data = data[~data[geography].duplicated(keep=False)]
    return (
        data[[name_col, "obs_value"]]
        .rename(columns={name_col: "country", "obs_value": "population"})
        .sort_values("population", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


@st.cache_data(ttl=86400, show_spinner=False)
def country_origin_breakdown(pop_type: str, host_code: str, period: str) -> pd.DataFrame:
    """
    Retrieve origin-country records for one hosting country and reporting period.
    The custom dimensions retain the required population type and filtered
    hosting-country dimension, then add country of origin as the breakdown.
    """
    params = {
        "c[pop_type]": pop_type,
        "c[ref_area_adm0]": host_code,
        "time_period": f"eq:{period}",
        "dimensions": "pop_type,ref_area_adm0,area_ori_adm0",
        "sort": "obs_value:desc",
    }
    data = _fetch_all(params)
    required = {"pop_type", "ref_area_adm0", "area_ori_adm0", "time_period", "obs_value"}
    missing = required.difference(data.columns)
    if missing:
        raise UNHCRDataError(
            "UNHCR origin breakdown is missing fields: " + ", ".join(sorted(missing))
        )
    data["obs_value"] = pd.to_numeric(data["obs_value"], errors="coerce")
    data = data[
        data["pop_type"].astype("string").eq(pop_type)
        & data["ref_area_adm0"].astype("string").eq(host_code)
        & data["time_period"].astype("string").eq(period)
    ].dropna(subset=["obs_value"])

    # _T is the explicit total; _X is unspecified origin. Neither is a country.
    origin = data[
        ~data["area_ori_adm0"].astype("string").isin(["_T", "_X"])
    ].copy()
    label_col = "area_ori_adm0_label"
    name_col = label_col if label_col in origin.columns else "area_ori_adm0"
    origin = origin[["area_ori_adm0", name_col, "obs_value"]].drop_duplicates()
    # Do not silently aggregate or choose between conflicting records.
    origin = origin[~origin["area_ori_adm0"].duplicated(keep=False)]
    return (
        origin[[name_col, "obs_value"]]
        .rename(columns={name_col: "country_of_origin", "obs_value": "population"})
        .sort_values("population", ascending=False)
        .reset_index(drop=True)
    )


@st.cache_data(ttl=86400, show_spinner=False)
def country_trend(pop_type: str, geo_code: str, geography: str) -> pd.DataFrame:
    if geography not in ("ref_area_adm0", "area_ori_adm0"):
        return pd.DataFrame(columns=["time_period", "population"])
    params = {
        "c[pop_type]": pop_type,
        f"c[{geography}]": geo_code,
        "dimensions": "default",
        "sort": "time_period:asc",
    }
    data = _fetch_all(params)
    if data.empty or "time_period" not in data.columns or "obs_value" not in data.columns:
        return pd.DataFrame(columns=["time_period", "population"])
    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    if opposite in data.columns:
        data = data[data[opposite].astype("string").eq("_T")]
    data["obs_value"] = pd.to_numeric(data["obs_value"], errors="coerce")
    data = data.dropna(subset=["obs_value"])
    data = data[~data["time_period"].duplicated(keep=False)]
    return data[["time_period", "obs_value"]].rename(columns={"obs_value": "population"}).sort_values("time_period").reset_index(drop=True)


@st.cache_data(ttl=86400, show_spinner=False)

def country_historical_comparison(
    frame: pd.DataFrame,
    pop_type: str,
    geography: str,
    country_codes: list[str],
) -> pd.DataFrame:
    """Return unique country-period totals for selected countries and one geography."""
    columns = ["time_period", "country_code", "country", "population"]
    if geography not in ("ref_area_adm0", "area_ori_adm0") or geography not in frame.columns:
        return pd.DataFrame(columns=columns)
    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    if opposite not in frame.columns:
        return pd.DataFrame(columns=columns)
    data = frame[
        frame["pop_type"].astype("string").eq(pop_type)
        & frame[geography].astype("string").isin([str(code) for code in country_codes])
        & frame[opposite].astype("string").eq("_T")
    ].copy()
    if data.empty:
        return pd.DataFrame(columns=columns)
    label_col = f"{geography}_label"
    data["population"] = pd.to_numeric(data["obs_value"], errors="coerce")
    data = data.dropna(subset=["time_period", "population"])
    keys = [geography, "time_period"]
    if data.duplicated(keys, keep=False).any():
        duplicated = data[data.duplicated(keys, keep=False)]
        ambiguous = set(zip(duplicated[geography].astype(str), duplicated["time_period"].astype(str)))
        data = data[
            ~data.apply(lambda row: (str(row[geography]), str(row["time_period"])) in ambiguous, axis=1)
        ]
    data["country"] = data[label_col] if label_col in data.columns else data[geography]
    return (
        data.rename(columns={geography: "country_code"})
        [["time_period", "country_code", "country", "population"]]
        .drop_duplicates()
        .sort_values(["time_period", "country"])
        .reset_index(drop=True)
    )


def population_period_coverage(pop_type: str) -> pd.DataFrame:
    """
    Retrieve the full available reporting-period history for one population type.
    Uses only population type and period dimensions to keep the response compact.
    """
    params = {
        "c[pop_type]": pop_type,
        "dimensions": "pop_type,time_period",
        "sort": "time_period:asc",
    }
    data = _fetch_all(params)
    required = {"pop_type", "time_period"}
    missing = required.difference(data.columns)
    if missing:
        raise UNHCRDataError(
            "UNHCR period-coverage response is missing fields: " + ", ".join(sorted(missing))
        )
    data = data[data["pop_type"].astype("string").eq(pop_type)].copy()
    data["time_period"] = data["time_period"].astype("string")
    data = data.dropna(subset=["time_period"])
    if data.empty:
        return pd.DataFrame(columns=["time_period", "record_count"])
    coverage = (
        data.groupby("time_period", dropna=False)
        .size()
        .rename("record_count")
        .reset_index()
        .sort_values("time_period")
        .reset_index(drop=True)
    )
    return coverage


def country_period_changes(
    frame: pd.DataFrame,
    pop_type: str,
    geography: str,
    earlier_period: str,
    later_period: str,
) -> pd.DataFrame:
    """Compare unique country totals across two observed periods; never fill absent values with zero."""
    columns = ["country_code", "country", "earlier_population", "later_population", "absolute_change", "percentage_change"]
    if geography not in ("ref_area_adm0", "area_ori_adm0") or geography not in frame.columns:
        return pd.DataFrame(columns=columns)
    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    data = frame[
        frame["pop_type"].astype("string").eq(pop_type)
        & frame["time_period"].astype("string").isin([earlier_period, later_period])
    ].copy()
    data = data[data[geography].notna() & ~data[geography].astype("string").isin(["_T", "_X"])]
    if opposite in data.columns:
        data = data[data[opposite].astype("string").eq("_T")]
    label_col = geography + "_label"
    name_col = label_col if label_col in data.columns else geography
    data["obs_value"] = pd.to_numeric(data["obs_value"], errors="coerce")
    data = data.dropna(subset=["obs_value"])
    keys = [geography, "time_period"]
    if data.duplicated(keys, keep=False).any():
        return pd.DataFrame(columns=columns)
    pivot = data.pivot(index=geography, columns="time_period", values="obs_value")
    if earlier_period not in pivot.columns or later_period not in pivot.columns:
        return pd.DataFrame(columns=columns)
    pivot = pivot.dropna(subset=[earlier_period, later_period]).copy()
    if pivot.empty:
        return pd.DataFrame(columns=columns)
    names = data.drop_duplicates(geography).set_index(geography)[name_col]
    result = pd.DataFrame({
        "country_code": pivot.index.astype(str),
        "country": names.reindex(pivot.index).astype(str).values,
        "earlier_population": pivot[earlier_period].values,
        "later_population": pivot[later_period].values,
    })
    result["absolute_change"] = result["later_population"] - result["earlier_population"]
    result["percentage_change"] = result.apply(
        lambda row: (row["absolute_change"] / row["earlier_population"] * 100)
        if row["earlier_population"] != 0 else pd.NA,
        axis=1,
    )
    return result.sort_values("absolute_change", ascending=False).reset_index(drop=True)



def population_measure_type(pop_type: str) -> str:
    """Return the stock/flow classification documented by UNHCR for PopStatsOfficial."""
    return "flow" if pop_type in {"RET", "RDP", "NAT", "RASP"} else "stock"


def explicit_total_trend(frame: pd.DataFrame, pop_type: str) -> pd.DataFrame:
    """Build a time series only from unique explicit total rows; never sum country records."""
    columns = ["time_period", "population"]
    if not {"pop_type", "time_period", "obs_value"}.issubset(frame.columns):
        return pd.DataFrame(columns=columns)
    rows = []
    for period in sorted(frame["time_period"].dropna().astype(str).unique()):
        value = explicit_global_total(frame, pop_type, period)
        if value is not None:
            rows.append({"time_period": period, "population": value})
    return pd.DataFrame(rows, columns=columns)



def decade_comparison(frame: pd.DataFrame, pop_type: str) -> pd.DataFrame:
    """Summarize explicit global totals by decade without mixing stock and flow logic."""
    trend = explicit_total_trend(frame, pop_type)
    columns = ["decade", "population", "observed_periods", "summary_method"]
    if trend.empty:
        return pd.DataFrame(columns=columns)
    years = pd.to_numeric(trend["time_period"].astype(str).str[:4], errors="coerce")
    trend = trend.assign(year=years).dropna(subset=["year"]).copy()
    if trend.empty:
        return pd.DataFrame(columns=columns)
    trend["year"] = trend["year"].astype(int)
    trend["decade_start"] = (trend["year"] // 10) * 10
    measure = population_measure_type(pop_type)
    rows = []
    for decade_start, group in trend.groupby("decade_start", sort=True):
        group = group.sort_values(["year", "time_period"])
        if measure == "stock":
            selected = group.iloc[-1]
            value = float(selected["population"])
            method = "Last observed explicit total in decade (stock)"
        else:
            value = float(group["population"].mean())
            method = "Mean of observed period-specific explicit flows (not a decade total)"
        rows.append({
            "decade": f"{decade_start}s",
            "population": value,
            "observed_periods": int(len(group)),
            "summary_method": method,
        })
    return pd.DataFrame(rows, columns=columns)


def country_pressure_signals(
    frame: pd.DataFrame,
    pop_type: str,
    geography: str = "ref_area_adm0",
) -> pd.DataFrame:
    """
    Describe recent country-level stock changes using observed hosting totals only.
    Persistence is assessed across the latest four shared reporting periods; no
    missing observations are imputed and flow categories are rejected.
    """
    columns = [
        "country_code", "country", "previous_period", "latest_period",
        "previous_population", "latest_population", "absolute_change",
        "percentage_change", "increasing_across_four_observed_periods",
    ]
    if population_measure_type(pop_type) != "stock":
        return pd.DataFrame(columns=columns)
    required = {"pop_type", "time_period", "obs_value", geography}
    if not required.issubset(frame.columns) or geography not in ("ref_area_adm0", "area_ori_adm0"):
        return pd.DataFrame(columns=columns)

    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    data = frame[frame["pop_type"].astype("string").eq(pop_type)].copy()
    data = data[data[geography].notna() & ~data[geography].astype("string").isin(["_T", "_X"])]
    if opposite in data.columns:
        data = data[data[opposite].astype("string").eq("_T")]
    data["time_period"] = data["time_period"].astype("string")
    data["obs_value"] = pd.to_numeric(data["obs_value"], errors="coerce")
    data = data.dropna(subset=["time_period", "obs_value"])
    keys = [geography, "time_period"]
    if data.empty or data.duplicated(keys, keep=False).any():
        return pd.DataFrame(columns=columns)

    periods = sorted(data["time_period"].unique())
    if len(periods) < 2:
        return pd.DataFrame(columns=columns)
    recent_periods = periods[-4:]
    pivot = data.pivot(index=geography, columns="time_period", values="obs_value")
    latest_two = periods[-2:]
    pivot = pivot.dropna(subset=latest_two)
    if pivot.empty:
        return pd.DataFrame(columns=columns)

    label_col = geography + "_label"
    name_col = label_col if label_col in data.columns else geography
    names = data.drop_duplicates(geography).set_index(geography)[name_col]
    result = pd.DataFrame({
        "country_code": pivot.index.astype(str),
        "country": names.reindex(pivot.index).astype(str).values,
        "previous_period": latest_two[0],
        "latest_period": latest_two[1],
        "previous_population": pivot[latest_two[0]].values,
        "latest_population": pivot[latest_two[1]].values,
    })
    result["absolute_change"] = result["latest_population"] - result["previous_population"]
    result["percentage_change"] = result.apply(
        lambda row: row["absolute_change"] / row["previous_population"] * 100
        if row["previous_population"] != 0 else pd.NA,
        axis=1,
    )

    if len(recent_periods) == 4:
        complete = pivot.reindex(columns=recent_periods).dropna()
        persistent_codes = set(
            complete.index[
                (complete[recent_periods].diff(axis=1).iloc[:, 1:] > 0).all(axis=1)
            ].astype(str)
        )
        result["increasing_across_four_observed_periods"] = result["country_code"].isin(persistent_codes)
    else:
        result["increasing_across_four_observed_periods"] = pd.NA

    return result[columns].sort_values("absolute_change", ascending=False).reset_index(drop=True)
