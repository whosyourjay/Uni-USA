"""Shared multi-year institution-level freshman score helpers."""

from collections import defaultdict
from statistics import fmean, median

import ability
import calibrate_tests

ADMISSION_YEARS = tuple(range(2019, 2024))


def route_lookup(institutions, years=ADMISSION_YEARS):
    """Return annual and multi-year-mean SAT/ACT percentiles by institution."""
    unitids = {row["unitid"] for row in institutions}
    _, act_table = calibrate_tests.load_act_composite_percentiles()
    sat_tables = {
        year: calibrate_tests.load_sat_total_user_percentiles(year) for year in years
    }
    annual = {}
    grouped = defaultdict(list)
    for year in years:
        for unitid, admission in ability.load_admissions(year).items():
            if unitid not in unitids:
                continue
            for route, value in calibrate_tests.admission_route_centers(
                admission, year, act_table, sat_tables[year]
            ).items():
                value = round(value, 3)
                annual[(unitid, route, year)] = value
                grouped[(unitid, route)].append(value)
    means = {key: round(fmean(values), 3) for key, values in grouped.items()}
    return {**annual, **means}


def route_fields(unitid, routes):
    sat = routes.get((unitid, "SAT"), "")
    act = routes.get((unitid, "ACT"), "")
    values = [value for value in (sat, act) if value != ""]
    labels = [name for name, value in (("SAT", sat), ("ACT", act)) if value != ""]
    output = {
        "freshman_score": round(median(values), 3) if values else "",
        "sat_taker_percentile_mean_2019_2023": sat,
        "act_taker_percentile_mean_2019_2023": act,
        "freshman_score_basis": (
            "median of multi-year mean " + " and ".join(labels) if labels else ""
        ),
    }
    for year in ADMISSION_YEARS:
        output[f"sat_taker_percentile_{year}"] = routes.get(
            (unitid, "SAT", year), ""
        )
        output[f"act_taker_percentile_{year}"] = routes.get(
            (unitid, "ACT", year), ""
        )
    return output
