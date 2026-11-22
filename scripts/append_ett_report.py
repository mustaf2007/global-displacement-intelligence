"""Initialize or append a verified ETT JSON batch to the local registry.

Examples:
  python scripts/append_ett_report.py --initialize
  python scripts/append_ett_report.py --input path/to/verified_week.json

The input must be a JSON array of normalized observations. Review and verify
source figures before running; this script performs structural validation only.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ett_registry import append_observations
from src.ett_timeseries import build_ett_observations

REGISTRY = ROOT / "data" / "somalia_ett_observations.json"


def main():
    parser = argparse.ArgumentParser(description="Append verified Somalia ETT observations.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--initialize", action="store_true", help="Create the registry from the verified Week 19 snapshot.")
    group.add_argument("--input", type=Path, help="JSON array containing new normalized observations.")
    args = parser.parse_args()

    if REGISTRY.exists():
        existing = json.loads(REGISTRY.read_text(encoding="utf-8"))
    else:
        existing = []

    if args.initialize:
        incoming = build_ett_observations()
    else:
        incoming = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(incoming, list):
            raise ValueError("Input JSON must be an array of normalized observation objects.")

    updated = append_observations(existing, incoming)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Registry updated: {len(existing)} -> {len(updated)} observations")
    print(f"File: {REGISTRY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
