from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import requests

API_URL = "https://api-data.unhcr.org/api/v0/data/PopStatsOfficial"
CONSTRAINTS_URL = "https://api-data.unhcr.org/api/v0/constraints/PopStatsOfficial"
REQUIRED_FIELDS = {"time_period", "pop_type", "obs_value"}
POPULATION_TYPES = ["REF_UNHCR", "REF_UNRWA", "ASY", "OIP", "IDP_UNHCR", "IDP_IDMC", "RET", "RDP", "NAT", "RASP", "STA"]


def main() -> int:
    checked_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "checked_at_utc": checked_at,
        "health_endpoint": "not_checked",
        "population_types": {},
    }

    try:
        health = requests.get(
            "https://api-data.unhcr.org/api/v0/health",
            headers={"User-Agent": "Global-Displacement-Intelligence/0.2"},
            timeout=(10, 20),
        )
        health.raise_for_status()
        summary["health_endpoint"] = "reachable"
        summary["health_http_status"] = health.status_code
    except requests.RequestException as exc:
        summary["health_endpoint"] = f"failed: {exc}"
        print(json.dumps(summary, indent=2))
        return 1

    try:
        constraints_response = requests.get(
            CONSTRAINTS_URL,
            headers={"User-Agent": "Global-Displacement-Intelligence/0.2"},
            timeout=(10, 20),
        )
        constraints_response.raise_for_status()
        constraints = constraints_response.json()
        data = constraints.get("data", [])
        dimensions = data.get("dimensions", []) if isinstance(data, dict) else []
        if isinstance(data, list):
            pop_dimension = next(
                (item for item in data if isinstance(item, dict) and item.get("dimension") == "pop_type"),
                None,
            )
        else:
            pop_dimension = next(
                (item for item in dimensions if isinstance(item, dict) and item.get("dimension") == "pop_type"),
                None,
            )
        if not pop_dimension:
            raise ValueError("The constraints response does not expose the pop_type dimension.")
        valid_types = [item["code"] for item in pop_dimension.get("values", []) if item.get("has_data")]
        summary["valid_population_types_from_constraints"] = valid_types
    except (requests.RequestException, ValueError) as exc:
        summary["constraints_error"] = str(exc)

    configured_missing = sorted(set(POPULATION_TYPES).difference(valid_types))
    summary["configured_population_types_missing_from_constraints"] = configured_missing
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
                headers={"User-Agent": "Global-Displacement-Intelligence/0.2"},
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

        missing = REQUIRED_FIELDS.difference(rows[0])
        if missing:
            summary["population_types"][pop_type] = {
                "status": "missing_fields",
                "missing_fields": sorted(missing),
            }
            continue

        invalid = 0
        for row in rows:
            try:
                float(row["obs_value"])
            except (TypeError, ValueError, KeyError):
                invalid += 1

        pagination = payload.get("pagination")
        pagination_ok = (
            isinstance(pagination, dict)
            and isinstance(pagination.get("has_next"), bool)
            and isinstance(pagination.get("page"), int)
        )
        periods = [str(row["time_period"]) for row in rows if row.get("time_period")]
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
    failed.extend(configured_missing)
    summary["overall_status"] = "ok" if not failed else "warning"
    summary["population_types_with_issues"] = failed
    print(json.dumps(summary, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
