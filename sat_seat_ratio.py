#!/usr/bin/env python3
"""Compare each school's q25 test bars with the national pool that clears them.

A published q25 bar sits above three quarters of that route's enrolled
submitters, so the seats the bar competes for are 0.75 of the route's submitter
count.  The pool is the number of national test takers who clear the same bar.
SAT and ACT pools and seats are summed before dividing, and the ratio is
averaged over the years a school reports.
"""

from collections import defaultdict
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from statistics import fmean
import re
import subprocess

import ability
import calibrate_tests
import pathways


ROOT = Path(__file__).parent
YEARS = (2017, 2018, 2019)
ABOVE_Q25_SHARE = 0.75
SCHOOLS = {
    166683: "Massachusetts Institute of Technology",
    115409: "Harvey Mudd College",
    110404: "California Institute of Technology",
    144050: "University of Chicago",
    186131: "Princeton University",
}


@lru_cache(maxsize=None)
def national_sat_takers(year):
    path = ROOT / "sources" / f"{year}-total-group-sat-report.pdf"
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    compact = "".join(result.stdout.split())
    counts = re.findall(r"\d{1,3}(?:,\d{3}){2}", compact)
    if not counts:
        raise ValueError(f"Could not find SAT test-taker count in {path.name}")
    total = int(counts[0].replace(",", ""))
    if not 1_000_000 < total < 3_000_000:
        raise ValueError(f"Implausible SAT test-taker count: {total:,}")
    return total


@lru_cache(maxsize=None)
def national_act_counts(year):
    """Composite frequencies for the tested class nearest to `year`."""
    counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    return counts


def route_pools(admission, sat_table, sat_takers, act_counts):
    """National takers clearing each reported q25 bar, and the seats above it."""
    pools = {}
    sat_bar = sum(
        pathways.number(admission.get(field)) for field in ("SATVR25", "SATMT25")
    )
    sat_submitters = pathways.number(admission.get("SATNUM"))
    if sat_bar > 0 and sat_submitters > 0:
        percentile = calibrate_tests.interpolate(sat_table, sat_bar)
        pools["sat"] = {
            "bar": sat_bar,
            "pool": sat_takers * (1 - percentile / 100),
            "seats": ABOVE_Q25_SHARE * sat_submitters,
        }
    act_bar = pathways.number(admission.get("ACTCM25"))
    act_submitters = pathways.number(admission.get("ACTNUM"))
    if act_bar > 0 and act_submitters > 0:
        pools["act"] = {
            "bar": act_bar,
            "pool": sum(
                count for score, count in act_counts.items() if score >= act_bar
            ),
            "seats": ABOVE_Q25_SHARE * act_submitters,
        }
    return pools


def pool_ratio(pools):
    """Summed SAT and ACT pools per summed seat, or None without a bar."""
    seats = sum(route["seats"] for route in pools.values())
    if not seats:
        return None
    return sum(route["pool"] for route in pools.values()) / seats


def year_pools(year):
    """Every school's route pools for one year, keyed by institution."""
    act_counts = national_act_counts(year)
    sat_table = calibrate_tests.load_sat_total_user_percentiles(year)
    sat_takers = national_sat_takers(year)
    pools = {}
    for unitid, admission in ability.load_admissions(year).items():
        school = route_pools(admission, sat_table, sat_takers, act_counts)
        if school:
            pools[unitid] = school
    return pools


def claimed_seats(pools):
    """Seats behind every bar at or above each school's own, one route at a time.

    Schools sharing a bar share a total, so the coarse integer ACT composite
    does not order identical schools at random."""
    entries = defaultdict(list)
    for unitid, school in pools.items():
        for route, values in school.items():
            entries[route].append((values["bar"], unitid, values["seats"]))
    claimed = defaultdict(dict)
    for route, route_entries in entries.items():
        running = 0.0
        route_entries.sort(key=lambda entry: -entry[0])
        for _, tied in groupby(route_entries, key=lambda entry: entry[0]):
            tied = list(tied)
            running += sum(seats for _, _, seats in tied)
            for _, unitid, _ in tied:
                claimed[route][unitid] = running
    return claimed


def cumulative_pool_ratio(school, claimed, unitid):
    """Pool clearing a school's bar per seat at that bar or above."""
    seats = sum(claimed[route][unitid] for route in school)
    if not seats:
        return None
    return sum(values["pool"] for values in school.values()) / seats


def pool_ratio_means(unitids, years=YEARS):
    """Mean pool-to-seat ratio by institution over the reporting years."""
    ratios = defaultdict(list)
    for year in years:
        pools = year_pools(year)
        claimed = claimed_seats(pools)
        for unitid in unitids:
            school = pools.get(unitid)
            if not school:
                continue
            ratio = cumulative_pool_ratio(school, claimed, unitid)
            if ratio is not None:
                ratios[unitid].append(ratio)
    return {unitid: round(fmean(values), 2) for unitid, values in ratios.items()}


def annual_rows():
    output = []
    for year in YEARS:
        pools = year_pools(year)
        claimed = claimed_seats(pools)
        sat_takers = national_sat_takers(year)
        for unitid, school in SCHOOLS.items():
            school_pools = pools[unitid]
            row = {"school": school, "year": year, "sat_test_takers": sat_takers}
            for route in ("sat", "act"):
                values = school_pools.get(route, {})
                row[f"{route}_q25_bar"] = values.get("bar", "")
                row[f"{route}_pool"] = round(values["pool"]) if values else ""
                row[f"{route}_seats"] = round(values["seats"], 2) if values else ""
                row[f"{route}_seats_at_or_above"] = (
                    round(claimed[route][unitid]) if values else ""
                )
            row["pool_per_seat"] = round(pool_ratio(school_pools), 2)
            row["pool_per_seat_at_or_above"] = round(
                cumulative_pool_ratio(school_pools, claimed, unitid), 2
            )
            output.append(row)
    return output


def average_rows(rows):
    fields = [key for key in rows[0] if key not in {"school", "year"}]
    output = []
    for school in SCHOOLS.values():
        values = [row for row in rows if row["school"] == school]
        result = {"school": school, "year": f"{YEARS[0]}-{YEARS[-1]} average"}
        for field in fields:
            present = [row[field] for row in values if row[field] != ""]
            result[field] = round(fmean(present), 2) if present else ""
        output.append(result)
    return output


def main():
    rows = annual_rows()
    averages = average_rows(rows)
    pathways.write_tsv(
        ROOT / "derived" / "top_q25_pool_ratios.tsv", rows + averages
    )
    for row in averages:
        print(
            f"{row['school']}: {row['pool_per_seat']:.2f} per own seat, "
            f"{row['pool_per_seat_at_or_above']:.2f} per seat at that bar or above"
        )


if __name__ == "__main__":
    main()
