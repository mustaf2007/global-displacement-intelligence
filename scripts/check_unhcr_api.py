from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import requests

API_URL = "https://api-data.unhcr.org/api/v0/data/PopStatsOfficial"
REQUIRED_FIELDS = {"time_period", "pop_type", "obs_value"}


def main() -> int:
    params = {
        "c[pop_type]": "REF_UNHCR",
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
        print(f"FAIL: UNHCR endpoint request failed: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("FAIL: API response root is not a JSON object.")
        return 1
    rows = payload.get("data")
    if not isinstance(rows, list):
        print("FAIL: API response does not contain a data list.")
        return 1
    if not rows:
        print("FAIL: API returned no observations for REF_UNHCR.")
        return 1

    missing = REQUIRED_FIELDS.difference(rows[0])
    if missing:
        print("FAIL: first observation is missing fields: " + ", ".join(sorted(missing)))
        return 1

    periods = sorted({str(row.get("time_period")) for row in rows if row.get("time_period")})
    if not periods:
        print("FAIL: no reporting period found in returned observations.")
        return 1

    invalid_values = []
    for index, row in enumerate(rows):
        try:
            float(row["obs_value"])
        except (TypeError, ValueError, KeyError):
            invalid_values.append(index)
    if invalid_values:
        print(f"FAIL: {len(invalid_values)} of {len(rows)} observations have non-numeric obs_value.")
        return 1

    pagination = payload.get("pagination")
    if pagination is not None and not isinstance(pagination, dict):
        print("FAIL: pagination metadata is not an object.")
        return 1

    result = {
        "status": "ok",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "observations_checked": len(rows),
        "latest_period_in_sample": max(periods),
        "pagination_metadata_present": isinstance(pagination, dict),
        "has_next": pagination.get("has_next") if isinstance(pagination, dict) else None,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
