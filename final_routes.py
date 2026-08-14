#!/usr/bin/env python3
"""Build one exhaustive credential and bachelor's-admission pathway table."""

from collections import defaultdict

import ability
import pathways
import scores
import special_routes
import transfer


ROUTE_ORDER = (
    "SAT",
    "ACT",
    "Open admission",
    "Automatic class-rank guarantee",
    "Recruited athletics",
    "Audition or portfolio",
    "Service-academy nomination",
    "School-record review without test evidence",
    "Transfer",
)
UT_AUSTIN_UNITID = 228778
HARVARD_UNITID = 166027


def freshman_route_shares(unitid, admission, characteristic, portfolio_share=0):
    """Assign every non-transfer freshman to exactly one route.

    IPEDS counts SAT and ACT submissions, not unique tested students.  We retain
    separate routes but fractionally de-overlap them: if their sum exceeds
    enrollment, the two counts are rescaled to exhaust enrollment.  Otherwise
    the unreported remainder stays unresolved.
    """
    if unitid in special_routes.SERVICE_ACADEMY_UNITIDS:
        return {"Service-academy nomination": 1.0}
    if pathways.number(characteristic.get("OPENADMP")) == 1:
        return {"Open admission": 1.0}

    special = {}
    if unitid == UT_AUSTIN_UNITID:
        special["Automatic class-rank guarantee"] = 0.75
    if unitid == HARVARD_UNITID:
        special["Recruited athletics"] = 0.095
    if pathways.number(admission.get("ADMCON6")) == 1:
        available = 1 - sum(special.values())
        special["Audition or portfolio"] = min(portfolio_share, available)
    remaining = 1 - sum(special.values())
    if remaining == 0:
        return special

    enrolled = pathways.number(admission.get("ENRLT"))
    sat = pathways.number(admission.get("SATNUM"))
    act = pathways.number(admission.get("ACTNUM"))
    if enrolled <= 0 or sat + act <= 0:
        special["School-record review without test evidence"] = remaining
        return special

    tested = min(enrolled, sat + act)
    shares = dict(special)
    shares["SAT"] = remaining * tested * sat / (sat + act) / enrolled
    shares["ACT"] = remaining * tested * act / (sat + act) / enrolled
    shares["School-record review without test evidence"] = 1 - sum(shares.values())
    return shares


def transfer_target(population, graduates):
    rows = pathways.cohort_pathway_rows(population, graduates)
    return next(row["people"] for row in rows if row["path"].startswith("Bachelor's, prior"))


def institution_route_rows(graduates, admissions, characteristics, population):
    """Estimate a route mixture for every final bachelor's institution."""
    outcome_direct = sum(row["direct_bachelors_8yr"] for row in graduates)
    outcome_transfer = sum(row["transfer_bachelors_8yr"] for row in graduates)
    fallback_share = outcome_transfer / (outcome_direct + outcome_transfer)
    target = transfer_target(population, graduates)
    raw_transfer = {
        row["unitid"]: row["bachelors_domestic"] * (
            row["transfer_share_bachelors_8yr"]
            if row["transfer_share_bachelors_8yr"] != ""
            else fallback_share
        )
        for row in graduates
    }
    scale = target / sum(raw_transfer.values())
    portfolio_counts = portfolio_bachelor_counts()

    output = []
    for graduate in graduates:
        unitid = graduate["unitid"]
        transfer_count = raw_transfer[unitid] * scale
        freshman_count = graduate["bachelors_domestic"] - transfer_count
        route_shares = freshman_route_shares(
            unitid,
            admissions.get(unitid, {}),
            characteristics.get(unitid, {}),
            portfolio_counts.get(unitid, 0) / graduate["bachelors_domestic"],
        )
        for route, share in route_shares.items():
            output.append({
                "unitid": unitid,
                "institution": graduate["institution"],
                "state": graduate["state"],
                "route": route,
                "estimated_bachelors": freshman_count * share,
                "share_institution_bachelors": (
                    freshman_count * share / graduate["bachelors_domestic"]
                ),
            })
        output.append({
            "unitid": unitid,
            "institution": graduate["institution"],
            "state": graduate["state"],
            "route": "Transfer",
            "estimated_bachelors": transfer_count,
            "share_institution_bachelors": transfer_count / graduate["bachelors_domestic"],
        })
    return output


def portfolio_bachelor_counts():
    """Domestic architecture and visual/performing-arts bachelor's awards."""
    totals = defaultdict(int)
    for row in pathways.bachelor_major_awards():
        if row["cip_code"].split(".", 1)[0] in {"04", "50"}:
            totals[row["unitid"]] += row["awards_domestic"]
    return totals


def national_route_rows(institution_rows, graduates, population):
    grouped = defaultdict(float)
    for row in institution_rows:
        grouped[row["route"]] += row["estimated_bachelors"]
    bachelor_total = sum(row["bachelors_domestic"] for row in graduates)
    counts = {route: round(grouped[route]) for route in ROUTE_ORDER}
    counts["School-record review without test evidence"] += (
        bachelor_total - sum(counts.values())
    )
    awards = domestic_award_levels()
    non_bachelor_awards = sum(awards[level] for level in (20, 21, 2, 3, 4))
    no_award = population - bachelor_total - non_bachelor_awards
    rows = [
        {
            "path": "No postsecondary award in annual flow",
            "people": no_award,
            "share_age18": no_award / population,
            "ability_measure": "Not yet separated by schooling history",
        },
        {
            "path": "Certificate under 12 weeks",
            "people": awards[20],
            "share_age18": awards[20] / population,
            "ability_measure": "Institution model pending",
        },
        {
            "path": "Certificate from 12 weeks to under one year",
            "people": awards[21],
            "share_age18": awards[21] / population,
            "ability_measure": "Institution model pending",
        },
        {
            "path": "Certificate from one to under two years",
            "people": awards[2],
            "share_age18": awards[2] / population,
            "ability_measure": "Institution model pending",
        },
        {
            "path": "Associate's degree",
            "people": awards[3],
            "share_age18": awards[3] / population,
            "ability_measure": "Two-year institution model pending",
        },
        {
            "path": "Two-to-four-year postsecondary certificate",
            "people": awards[4],
            "share_age18": awards[4] / population,
            "ability_measure": "Institution model pending",
        },
    ]
    measures = {
        "SAT": "SAT test-taker percentiles",
        "ACT": "ACT test-taker percentiles",
        "Open admission": "Not yet scored",
        "Automatic class-rank guarantee": "Top-six-percent rank proxy",
        "Recruited athletics": "Separate adjustment pending",
        "Audition or portfolio": "Separate adjustment pending",
        "Service-academy nomination": "Academy SAT/ACT plus screens",
        "School-record review without test evidence": "GPA/rank calibration pending",
        "Transfer": "Origin-school mixture; GPA update pending",
    }
    for route in ROUTE_ORDER:
        rows.append({
            "path": route,
            "people": counts[route],
            "share_age18": counts[route] / population,
            "ability_measure": measures[route],
        })
    if abs(sum(row["people"] for row in rows) - population) > 0.01:
        raise ValueError("Final pathway table does not exhaust the age-18 population")
    return rows


def domestic_award_levels():
    """Domestic annual award totals for the pre-bachelor levels in C2023_A."""
    totals = defaultdict(int)
    for row in pathways.first_major_awards():
        if row["award_level"] in {2, 3, 4, 20, 21} and row["cip_code"] == "99":
            totals[row["award_level"]] += row["awards_domestic"]
    return totals


def route_score_rows(institution_rows, graduates):
    lookup = scores.route_lookup(graduates)
    _, transfer_summary = transfer.build_transfer_tables()
    transfer_score = next(
        row["weighted_median_freshman_score"]
        for row in transfer_summary
        if row["origin_type"] == "All origins"
    )
    grouped = defaultdict(list)
    for row in institution_rows:
        score = lookup.get((row["unitid"], row["route"]))
        if row["route"] == "Automatic class-rank guarantee":
            score = 97.0
        if row["route"] == "Service-academy nomination":
            fields = scores.route_fields(row["unitid"], lookup)
            score = fields["freshman_score"] or None
        if row["route"] == "Transfer":
            score = transfer_score
        if score is not None:
            grouped[row["route"]].append((score, row["estimated_bachelors"]))

    output = []
    totals = defaultdict(float)
    for row in institution_rows:
        totals[row["route"]] += row["estimated_bachelors"]
    for route in ROUTE_ORDER:
        observed = grouped[route]
        weight = sum(count for _, count in observed)
        output.append({
            "route": route,
            "estimated_bachelors": totals[route],
            "scored_bachelors": weight,
            "score_coverage": weight / totals[route] if totals[route] else 0,
            "provisional_ability_center": (
                sum(score * count for score, count in observed) / weight
                if weight else ""
            ),
        })
    return output


def build_tables():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    population = pathways.load_population()
    institution_rows = institution_route_rows(
        graduates,
        ability.load_admissions(),
        ability.load_characteristics(),
        population,
    )
    return (
        institution_rows,
        national_route_rows(institution_rows, graduates, population),
        route_score_rows(institution_rows, graduates),
    )


def main():
    institution_rows, national_rows, score_rows = build_tables()
    pathways.write_tsv(pathways.DERIVED / "institution_final_routes.tsv", institution_rows)
    pathways.write_tsv(pathways.DERIVED / "final_admission_paths.tsv", national_rows)
    pathways.write_tsv(pathways.DERIVED / "final_route_scores.tsv", score_rows)
    print(f"wrote {len(national_rows)} exhaustive national pathways")


if __name__ == "__main__":
    main()
