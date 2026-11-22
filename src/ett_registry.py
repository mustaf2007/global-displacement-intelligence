"""Append-only registry helpers for normalized Somalia ETT observations."""
from copy import deepcopy

from src.ett_timeseries import validate_ett_observations


def observation_key(row):
    """Stable dimension key; category distinguishes reason-share records."""
    return tuple(row.get(field) for field in (
        "source", "period_start", "period_end", "indicator",
        "measure_type", "geography_type", "geography", "category",
    ))


def append_observations(existing, incoming):
    """Validate and append new records; reject duplicates rather than overwrite."""
    current = deepcopy(existing)
    additions = deepcopy(incoming)
    existing_validation = validate_ett_observations(current)
    incoming_validation = validate_ett_observations(additions)
    if not existing_validation["passed"]:
        raise ValueError("Existing registry failed validation; refusing to modify it.")
    if not incoming_validation["passed"]:
        raise ValueError("Incoming observations failed validation; refusing to append.")
    known = {observation_key(row) for row in current}
    duplicates = [i for i, row in enumerate(additions) if observation_key(row) in known]
    if duplicates:
        raise ValueError(f"Append rejected: {len(duplicates)} incoming observation key(s) already exist.")
    combined = current + additions
    combined_validation = validate_ett_observations(combined)
    if not combined_validation["passed"]:
        raise ValueError("Combined registry failed validation; refusing to append.")
    return combined
