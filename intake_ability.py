#!/usr/bin/env python3
"""Median age-18 ability of each school's graduates, on the national cohort scale.

Every ability figure here is a percentile of the whole age-18 population, not of
test takers.  The SAT and ACT together are treated as covering the top of that
population: their combined reach is `SAT + ACT - both`, and a score beating a
share `s` of its own test's takers is placed at cohort percentile
`100 * (1 - s * reach / cohort)`.

IPEDS publishes four bars per school-year - SAT and ACT quartiles - each of
which says how many enrolled submitters cleared a known ability level.  Both
tests land on the one cohort axis, so the four combine into a single intake
curve.  Students who sent neither test are assumed to sit below every bar.

The curve counts entrants, but the median is read among graduates.  Transfers in
arrive below every published bar, and the students who leave are drawn uniformly
from the freshman class, so the freshmen who stay keep the entering distribution.
"""

from collections import Counter, defaultdict
from statistics import NormalDist, fmean

import ability
import calibrate_tests
import final_routes
import pathways
import sat_seat_ratio

NORMAL = NormalDist()
DUAL_TAKER_ANCHOR = (2017, 589_753)
QUARTILE_MODEL = "normal"
IQR_Z = 2 * NORMAL.inv_cdf(0.75)
SOLVE_STEPS = 60
OUTPUT = pathways.DERIVED / "graduate_median_ability.tsv"


def national_act_takers(year):
    counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    return sum(counts.values())


def taker_product(year):
    return sat_seat_ratio.national_sat_takers(year) * national_act_takers(year)


def dual_takers(year):
    """Students sitting both tests, carried from the one year anyone counted.

    The 2018 concordance study matched 589,753 students from the 2017 graduating
    class who sat both the ACT and the redesigned SAT.  That is the matched
    sample, so it is a floor on the year's dual takers rather than a count of
    them: anyone pairing the ACT with the old SAT never entered it.  Nobody
    publishes a later figure, so the overlap moves with the product of the two
    taker pools, holding the 2017 association between sitting one and the other.
    Too low an overlap inflates the union and understates American percentiles.
    """
    anchor_year, anchor_count = DUAL_TAKER_ANCHOR
    return anchor_count * taker_product(year) / taker_product(anchor_year)


def cohort_reach(year):
    """Share of the age-18 cohort sitting at least one of the two tests."""
    union = (
        sat_seat_ratio.national_sat_takers(year)
        + national_act_takers(year)
        - dual_takers(year)
    )
    return union / pathways.load_population()


def cohort_percentile(taker_share_above, year):
    """Cohort percentile of a score that beats `taker_share_above` of its takers."""
    return 100 * (1 - taker_share_above * cohort_reach(year))


def sat_share_above(bar, table):
    """Share of national SAT takers at or above a total-score bar."""
    return max(0.0, 1 - calibrate_tests.interpolate(table, bar) / 100)


def act_share_above(bar, counts):
    """Share of national ACT takers at or above a composite bar."""
    total = sum(counts.values())
    return sum(count for score, count in counts.items() if score >= bar) / total


def uniform_share(percentile, low, high):
    """Submitters at or above `percentile` when each quartile spreads evenly.

    The middle half fills the reported inter-quartile band, the top quarter
    fills everything above it, and the bottom quarter fills everything below.
    """
    if percentile >= 100:
        return 0.0
    if percentile >= high:
        return 0.25 * (100 - percentile) / (100 - high)
    if percentile >= low:
        return 0.25 + 0.5 * (high - percentile) / (high - low)
    if percentile <= 0:
        return 1.0
    return 0.75 + 0.25 * (low - percentile) / low


def normal_share(percentile, low, high):
    """Submitters at or above `percentile` under a normal pinned to both bars."""
    if not 0 < percentile < 100:
        return 1.0 if percentile <= 0 else 0.0
    low_z, high_z = NORMAL.inv_cdf(low / 100), NORMAL.inv_cdf(high / 100)
    sigma = (high_z - low_z) / IQR_Z
    if sigma <= 0:
        return 0.0
    return 1 - NORMAL.cdf((NORMAL.inv_cdf(percentile / 100) - (low_z + high_z) / 2) / sigma)


def route_share(percentile, low, high, model=None):
    if high <= low:
        return None
    if (model or QUARTILE_MODEL) == "normal":
        return normal_share(percentile, low, high)
    return uniform_share(percentile, low, high)


def school_routes(admission, year, sat_table, act_counts):
    """Submitter count and the two cohort-percentile bars for each test route."""
    routes = {}
    sat_bar = {
        edge: sum(
            pathways.number(admission.get(f"SAT{part}{edge}"))
            for part in ("VR", "MT")
        )
        for edge in ("25", "75")
    }
    sat_submitters = pathways.number(admission.get("SATNUM"))
    if sat_submitters > 0 and 0 < sat_bar["25"] < sat_bar["75"]:
        routes["sat"] = {
            "n": sat_submitters,
            "low": cohort_percentile(sat_share_above(sat_bar["25"], sat_table), year),
            "high": cohort_percentile(sat_share_above(sat_bar["75"], sat_table), year),
        }
    act_bar = {
        edge: pathways.number(admission.get(f"ACTCM{edge}")) for edge in ("25", "75")
    }
    act_submitters = pathways.number(admission.get("ACTNUM"))
    if act_submitters > 0 and 0 < act_bar["25"] < act_bar["75"]:
        routes["act"] = {
            "n": act_submitters,
            "low": cohort_percentile(act_share_above(act_bar["25"], act_counts), year),
            "high": cohort_percentile(act_share_above(act_bar["75"], act_counts), year),
        }
    return routes


def distinct_submitters(routes, entrants):
    """Entrants who sent at least one score, capped by the entering class.

    IPEDS counts a dual submitter twice, so the sum overstates the class
    whenever it exceeds it; the excess is the smallest overlap consistent with
    both counts.
    """
    sent = sum(route["n"] for route in routes.values())
    return min(sent, entrants) if entrants > 0 else sent


def intake_above(percentile, routes, submitters):
    """Enrolled submitters at or above a cohort percentile.

    A student who sent both tests is counted once by each route, and dual
    submitters clear a bar at the same rate as the whole submitting group, so
    the overlap cancels out of the submitter-weighted share.
    """
    weighted, sent = 0.0, 0
    for route in routes.values():
        share = route_share(percentile, route["low"], route["high"])
        if share is None:
            continue
        weighted += route["n"] * share
        sent += route["n"]
    if not sent:
        return None
    return submitters * weighted / sent


def solve_percentile(target, routes, submitters):
    """Cohort percentile leaving `target` enrolled submitters above it."""
    if intake_above(0.0, routes, submitters) is None:
        return None
    if submitters < target:
        return None
    low, high = 0.0, 100.0
    for _ in range(SOLVE_STEPS):
        middle = (low + high) / 2
        if intake_above(middle, routes, submitters) >= target:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def graduate_target(graduates, transfers, entrants):
    """Entrants sitting above the median graduate under the transfer model.

    Transfers in are treated as the school's weakest students, so the median
    graduate is a freshman unless transfers take more than half the degrees.
    Leaving is independent of ability, which leaves the surviving freshmen with
    the entering class's distribution: the median graduate's quantile among
    direct graduates is its quantile among entrants.
    """
    direct = graduates - transfers
    if entrants <= 0 or direct <= graduates / 2:
        return None
    return entrants * (graduates / 2) / direct


def year_result(admission, year, target, sat_table, act_counts):
    """One school-year's median, or the reason there is not one."""
    routes = school_routes(admission, year, sat_table, act_counts)
    if not routes:
        return None
    entrants = pathways.number(admission.get("ENRLT"))
    submitters = distinct_submitters(routes, entrants)
    result = {"submitters": submitters, "entrants": entrants, "median": None}
    if target is None:
        result["reason"] = "most degrees go to transfers"
        return result
    median = solve_percentile(target, routes, submitters)
    if median is None:
        result["reason"] = "median graduate sent no score"
        return result
    return result | {"median": median, "bracketed": bracketing(median, routes)}


def year_results(year, graduates, transfers):
    """Every school reporting bars that year, keyed by unitid."""
    sat_table = calibrate_tests.load_sat_total_user_percentiles(year)
    act_counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    results = {}
    for unitid, admission in ability.load_admissions(year).items():
        awards = graduates.get(unitid, 0)
        if awards <= 0:
            continue
        target = graduate_target(
            awards, transfers.get(unitid, 0.0),
            pathways.number(admission.get("ENRLT")),
        )
        result = year_result(admission, year, target, sat_table, act_counts)
        if result is not None:
            results[unitid] = result
    return results


def year_percentiles(years=sat_seat_ratio.YEARS):
    """Graduate median percentile, keyed by institution and admission year."""
    graduates = pathways.mean_bachelors()
    transfers = final_routes.transfer_graduates()
    return {
        (unitid, year): result["median"]
        for year in years
        for unitid, result in year_results(year, graduates, transfers).items()
        if result["median"] is not None
    }


def bracketing(percentile, routes):
    """Whether the solved median sits inside some route's reported quartiles.

    Outside that band the answer rests on the shape assumed for a tail rather
    than on a published bar, and the two quartile models diverge sharply.
    """
    return any(
        route["low"] <= percentile <= route["high"] for route in routes.values()
    )


def row_status(scored, results):
    if not scored:
        return Counter(result["reason"] for result in results).most_common(1)[0][0]
    if not any(result["bracketed"] for result in scored):
        return "median outside the reported quartiles"
    return ""


def school_rows(years=sat_seat_ratio.YEARS):
    """One row per school, averaging the per-year graduate medians."""
    graduates = pathways.mean_bachelors()
    transfers = final_routes.transfer_graduates()
    directory = pathways.load_directory()
    collected = defaultdict(list)
    for year in years:
        for unitid, result in year_results(year, graduates, transfers).items():
            collected[unitid].append(result)
    rows = []
    for unitid, results in collected.items():
        entry = directory.get(unitid)
        scored = [result for result in results if result["median"] is not None]
        rows.append({
            "unitid": unitid,
            "school": entry["INSTNM"] if entry else "",
            "bachelors": round(graduates[unitid], 1),
            "entrants": round(fmean(r["entrants"] for r in results), 1),
            "submitters": round(fmean(r["submitters"] for r in results), 1),
            "transfer_share": round(transfers.get(unitid, 0.0) / graduates[unitid], 3),
            "median_percentile": (
                round(fmean(r["median"] for r in scored), 3) if scored else ""
            ),
            "years": len(results),
            "bracketed_years": sum(result.get("bracketed", False) for result in scored),
            "status": row_status(scored, results),
        })
    rows.sort(key=lambda row: (row["median_percentile"] == "",
                               -(row["median_percentile"] or 0)))
    return rows


def main():
    rows = school_rows()
    pathways.write_tsv(OUTPUT, rows)
    flagged = Counter(row["status"] for row in rows if row["status"])
    print(f"{len(rows)} schools; reach "
          + ", ".join(f"{year} {100 * cohort_reach(year):.1f}%"
                      for year in sat_seat_ratio.YEARS))
    for status, count in flagged.most_common():
        print(f"  {count:>5} {status}")
    print(f"\n{'school':<44} {'grads':>7} {'subs':>7} {'median':>8}")
    for row in (row for row in rows if not row["status"]):
        if row["bachelors"] < 200:
            continue
        print(f"{(row['school'] or row['unitid'])[:44]:<44} {row['bachelors']:>7.0f} "
              f"{row['submitters']:>7.0f} {row['median_percentile']:>8.2f}")


if __name__ == "__main__":
    main()
