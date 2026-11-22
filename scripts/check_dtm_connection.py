"""Run a manual, read-only connectivity and schema check against IOM DTM API v3.

The script makes no request unless DTMAPI_SUBSCRIPTION_KEY is configured.
It prints summary metadata only; it does not save or publish API records.
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from src.dtm_api import DTMConnectorError, fetch_idp_data
from src.dtm_quality import profile_idp_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check access to aggregated IOM DTM IDP assessment data."
    )
    parser.add_argument("--country", default="Somalia", help="Country name (default: Somalia)")
    parser.add_argument(
        "--admin-level", type=int, choices=(0, 1, 2), default=1,
        help="Geographic level: 0 country, 1 first-level, 2 second-level (default: 1)",
    )
    parser.add_argument("--from-date", help="Optional start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="Optional end date (YYYY-MM-DD)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not os.getenv("DTMAPI_SUBSCRIPTION_KEY"):
        print("NOT CONFIGURED: set DTMAPI_SUBSCRIPTION_KEY in your environment.")
        print("No API request was made.")
        return 2

    try:
        frame = fetch_idp_data(
            country_name=args.country,
            admin_level=args.admin_level,
            from_reporting_date=args.from_date,
            to_reporting_date=args.to_date,
        )
    except (DTMConnectorError, ValueError) as exc:
        print(f"DTM API CHECK FAILED: {exc}")
        return 1

    print(f"Country: {args.country}")
    print(f"Administrative level: {args.admin_level}")
    print(f"Rows returned: {len(frame)}")
    print(f"Columns returned: {', '.join(map(str, frame.columns)) or '(none)'}")

    if frame.empty:
        print("RESULT: no records returned for this query; coverage is not established.")
        return 3

    profile = profile_idp_data(frame, args.admin_level)
    print(f"Basic quality status: {profile['status']}")
    print(f"Missing required columns: {profile['missing_required_columns']}")
    print(f"Null counts: {profile['null_counts']}")
    print(f"Invalid reporting dates: {profile['invalid_reporting_dates']}")
    print(f"Invalid population values: {profile['invalid_population_values']}")
    print(f"Negative population values: {profile['negative_population_values']}")
    print(f"Exact duplicate rows: {profile['exact_duplicate_rows']}")

    date_column = "reportingDate"
    if date_column in frame.columns:
        dates = pd.to_datetime(frame[date_column], errors="coerce").dropna()
        if not dates.empty:
            print(f"Reporting-date range: {dates.min().date()} to {dates.max().date()}")

    print("NOTE: this endpoint provides IDP population assessment snapshots, not ETT weekly arrival flows.")
    return 0 if profile["status"] == "passed_basic_checks" else 4


if __name__ == "__main__":
    sys.exit(main())
