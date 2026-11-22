from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import requests

API_URL = "https://api-data.unhcr.org/api/v0/data/PopStatsOfficial"
CONSTRAINTS_URL = "https://api-data.unhcr.org/api/v0/constraints/PopStatsOfficial"
REQUIRED_FIELDS = {"time_period", "pop_type", "obs_value"}
POPULATION_TYPES = ["REF_UNHCR", "REF_UNRWA", "ASY", "OIP", "IDP_UNHCR", "IDP_IDMC", "RET", "RDP", "NAT", "RASP", "STA"]
HEADERS = {"User-Agent": "Global-Displacement-Intelligence/0.2"}


def _population_type_codes(constraints: dict) -> set[str]:
    """Extract population-type codes with data from supported constraints shapes."""
    data = constraints.get("data", [])
    if isinstance(data, list):
        dimensions = data
    elif isinstance(data, dict):
        dimensions = data.get("dimensions", [])
    else:
        dimensions = []

    if not isinstance(dimensions, list):
        raise ValueError("The constraints response has an invalid dimensions structure.")

    dimension = next(
        (
            item for item in dimensions
            if isinstance(item, dict) and item.get("dimension") == "pop_type"
        ),
        None,
    )
    if dimension is None:
        raise ValueError("The constraints response does not expose the pop_type dimension.")

    values = dimension.get("values", [])
    if not isinstance(values, list):
        raise ValueError("The pop_type constraints values are not a list.")

    codes = {
        item.get("code")
        for item in values
        if isinstance(item, dict)
        and item.get("has_data") is True
        and isinstance(item.get("code"), str)
        and item.get("code")
    }
    if not codes:
        raise ValueError("The pop_type constraints dimension contains no usable codes.")
    return codes


def main() -> int:
    checked_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "checked_at_utc": checked_at,
        "health_endpoint": "not_checked",
        "constraints_status": "not_checked",
        "population_types": {},
    }

    try:
        health = requests.get(
            "https://api-data.unhcr.org/api/v0/health",
            headers=HEADERS,
            timeout=(10, 20),
        )
        health.raise_for_status()
        summary["health_endpoint"] = "reachable"
        summary["health_http_status"] = health.status_code
    except requests.RequestException as exc:
        summary["health_endpoint"] = f"failed: {exc}"
        print(json.dumps(summary, indent=2))
        return 1

    valid_types: set[str] | None = None
    try:
        constraints_response = requests.get(
            CONSTRAINTS_URL,
            headers=HEADERS,
            timeout=(10, 20),
        )
        constraints_response.raise_for_status()
        valid_types = _population_type_codes(constraints_response.json())
        summary["constraints_status"] = "ok"
        summary["valid_population_types_from_constraints"] = sorted(valid_types)
        configured_missing = sorted(set(POPULATION_TYPES).difference(valid_types))
        summary["configured_population_types_missing_from_constraints"] = configured_missing
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        summary["constraints_status"] = "failed"
        summary["constraints_error"] = str(exc)
        summary["configured_population_types_missing_from_constraints"] = None

    for pop_type in POPULATION_TYPES:
        params = {
            "c[pop_type]": pop_type,
            "dimensions": "default",
            "sort": "time_period:desc",
            "page": 1,
            "page_size": 10,
        }
        try:
            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=(10, 30),
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            summary["population_types"][pop_type] = {"status": "request_failed", "error": str(exc)}
            continue

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            summary["population_types"][pop_type] = {"status": "invalid_response"}
            continue

        rows = payload["data"]
        if not rows:
            summary["population_types"][pop_type] = {"status": "no_observations"}
            continue

        if not isinstance(rows[0], dict):
            summary["population_types"][pop_type] = {"status": "invalid_row"}
            continue
        missing = REQUIRED_FIELDS.difference(rows[0])
        if missing:
            summary["population_types"][pop_type] = {
                "status": "missing_fields",
                "missing_fields": sorted(missing),
            }
            continue

        invalid = 0
        for row in rows:
            if not isinstance(row, dict):
                invalid += 1
                continue
            try:
                value = float(row["obs_value"])
                if not (value >= 0 and value < float("inf")):
                    invalid += 1
            except (TypeError, ValueError, KeyError):
                invalid += 1

        pagination = payload.get("pagination")
        pagination_ok = (
            isinstance(pagination, dict)
            and isinstance(pagination.get("has_next"), bool)
            and isinstance(pagination.get("page"), int)
        )
        periods = [str(row["time_period"]) for row in rows if isinstance(row, dict) and row.get("time_period")]
        status = "ok" if invalid == 0 and pagination_ok and periods else "data_quality_warning"
        summary["population_types"][pop_type] = {
            "status": status,
            "observations_checked": len(rows),
            "latest_period_in_sample": max(periods) if periods else None,
            "invalid_values": invalid,
            "pagination_metadata_valid": pagination_ok,
            "has_next": pagination.get("has_next") if isinstance(pagination, dict) else None,
        }

    failed = [
        code for code, result in summary["population_types"].items()
        if result.get("status") != "ok"
    ]
    if valid_types is not None:
        failed.extend(configured_missing)
    else:
        failed.append("constraints")
    summary["overall_status"] = "ok" if not failed else "warning"
    summary["population_types_with_issues"] = failed
    print(json.dumps(summary, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
