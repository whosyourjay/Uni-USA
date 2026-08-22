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

The curve counts entrants, but the median is read among graduates. Transfer
ability comes from the stack-ranked origin pool dealt to each destination.
Students who leave are drawn uniformly from the freshman class, so the freshmen
who stay keep the entering distribution.
"""

from collections import Counter, defaultdict
from functools import lru_cache
from statistics import fmean

from uniusa import (
    ability,
    calibrate_tests,
    final_routes,
    intake_curve,
    pathways,
    test_counts,
    transfer,
)
from uniusa.intake_curve import (
    distinct_submitters,
    intake_above,
    normal_share,
    route_share,
    solve_percentile,
    uniform_share,
)

DUAL_TAKER_ANCHOR = (2017, 589_753)
OUTPUT = pathways.DERIVED / "graduate_median_ability.tsv"


def national_act_takers(year):
    counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    return sum(counts.values())


def taker_product(year):
    return test_counts.national_sat_takers(year) * national_act_takers(year)


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
        test_counts.national_sat_takers(year)
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


def cohort_transfer_distribution(destination, year):
    """A destination's transfer-origin blocks on the age-cohort scale."""
    if not destination:
        return ()
    distribution = destination.get("distribution", ())
    if not distribution and destination.get("transfer_score", "") != "":
        distribution = ((destination["transfer_score"], 1.0),)
    return tuple(
        (cohort_percentile(1 - score / 100, year), weight)
        for score, weight in distribution
    )


def year_result(
    admission,
    year,
    graduates,
    transfers,
    transfer_distribution,
    sat_table,
    act_counts,
):
    """One school-year's median, or the reason there is not one."""
    routes = school_routes(admission, year, sat_table, act_counts)
    if not routes:
        return None
    entrants = pathways.number(admission.get("ENRLT"))
    submitters = distinct_submitters(routes, entrants)
    result = {"submitters": submitters, "entrants": entrants, "median": None}
    median = intake_curve.solve_graduate_median(
        routes,
        submitters,
        entrants,
        graduates,
        transfers,
        transfer_distribution,
    )
    if median is None:
        result["reason"] = "median graduate ability is unobserved"
        return result
    return result | {"median": median, "bracketed": bracketing(median, routes)}


def year_results(year, graduates, transfers, transfer_scores):
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
        transfer_count = transfers.get(unitid, 0.0)
        result = year_result(
            admission,
            year,
            awards,
            transfer_count,
            cohort_transfer_distribution(transfer_scores.get(unitid), year),
            sat_table,
            act_counts,
        )
        if result is not None:
            results[unitid] = result
    return results


@lru_cache(maxsize=None)
def default_transfer_scores():
    """Build destination transfer distributions for standalone model runs."""
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    institution_rows = final_routes.institution_route_rows(
        graduates,
        ability.load_admissions(),
        ability.load_characteristics(),
        pathways.load_population(),
    )
    return transfer.destination_scores(institution_rows, graduates)


def year_percentiles(years=test_counts.YEARS, transfer_scores=None):
    """Graduate median percentile, keyed by institution and admission year."""
    graduates = pathways.mean_bachelors()
    transfers = final_routes.transfer_graduates()
    transfer_scores = transfer_scores or default_transfer_scores()
    return {
        (unitid, year): result["median"]
        for year in years
        for unitid, result in year_results(
            year, graduates, transfers, transfer_scores
        ).items()
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


def school_rows(years=test_counts.YEARS, transfer_scores=None):
    """One row per school, averaging the per-year graduate medians."""
    graduates = pathways.mean_bachelors()
    transfers = final_routes.transfer_graduates()
    transfer_scores = transfer_scores or default_transfer_scores()
    directory = pathways.load_directory()
    collected = defaultdict(list)
    for year in years:
        for unitid, result in year_results(
            year, graduates, transfers, transfer_scores
        ).items():
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
                      for year in test_counts.YEARS))
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
