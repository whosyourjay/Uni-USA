"""Shared multi-year institution-level freshman score helpers."""

from collections import defaultdict
from statistics import fmean, median

import ability
import calibrate_tests
import pathways

ADMISSION_YEARS = tuple(range(2014, 2024))
SAT_ADMISSION_YEARS = tuple(range(2016, 2024))
TEST_SHARE_COLUMNS = ("satnum_pct", "actnum_pct", "no_test_pct")


def route_lookup(institutions, years=ADMISSION_YEARS):
    """Return annual and multi-year-mean SAT/ACT percentiles by institution."""
    unitids = {row["unitid"] for row in institutions}
    _, act_table = calibrate_tests.load_act_composite_percentiles()
    sat_tables = {
        year: calibrate_tests.load_sat_total_user_percentiles(year)
        for year in years
        if year in SAT_ADMISSION_YEARS
    }
    annual = {}
    grouped = defaultdict(list)
    for year in years:
        for unitid, admission in ability.load_admissions(year).items():
            if unitid not in unitids:
                continue
            for route, value in calibrate_tests.admission_route_centers(
                admission,
                year,
                act_table,
                sat_tables.get(year),
                include_sat=year in sat_tables,
            ).items():
                value = round(value, 3)
                annual[(unitid, route, year)] = value
                grouped[(unitid, route)].append(value)
    means = {key: round(fmean(values), 3) for key, values in grouped.items()}
    return {**annual, **means}


def test_share_means(years=ADMISSION_YEARS):
    """Mean SAT, ACT, and no-test percentages of the entering class.

    IPEDS counts submitters, not unique tested students, and never counts the
    students who submitted neither.  The remainder of an entering class bounds
    that group, so we average `SAT / ENRLT`, `ACT / ENRLT`, and
    `1 - (SAT + ACT) / ENRLT` over the years an institution reports any
    submitter.  Students who sent both tests fall in both submitter counts, so
    the three percentages need not sum to 100.  Years with no reported
    submitter are missing data, not unscored students.
    """
    totals = defaultdict(
        lambda: dict.fromkeys(TEST_SHARE_COLUMNS + ("years",), 0)
    )
    for year in years:
        for unitid, admission in ability.load_admissions(year).items():
            sat = pathways.number(admission.get("SATNUM"))
            act = pathways.number(admission.get("ACTNUM"))
            entrants = pathways.number(admission.get("ENRLT"))
            if entrants <= 0 or sat + act <= 0:
                continue
            shares = totals[unitid]
            shares["satnum_pct"] += 100 * sat / entrants
            shares["actnum_pct"] += 100 * act / entrants
            shares["no_test_pct"] += 100 * max(0, entrants - sat - act) / entrants
            shares["years"] += 1
    return {
        unitid: {
            column: round(shares[column] / shares["years"], 1)
            for column in TEST_SHARE_COLUMNS
        }
        for unitid, shares in totals.items()
    }


def route_fields(unitid, routes):
    sat = routes.get((unitid, "SAT"), "")
    act = routes.get((unitid, "ACT"), "")
    values = [value for value in (sat, act) if value != ""]
    labels = [name for name, value in (("SAT", sat), ("ACT", act)) if value != ""]
    output = {
        "freshman_score": round(median(values), 3) if values else "",
        "sat_taker_percentile": sat,
        "act_taker_percentile": act,
        "freshman_score_basis": (
            "median of multi-year mean " + " and ".join(labels) if labels else ""
        ),
    }
    return output
