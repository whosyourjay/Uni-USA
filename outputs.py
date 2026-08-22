#!/usr/bin/env python3
"""Build the canonical school and major tables for the endpoint model."""

import argparse
import re
from collections import Counter
from html.parser import HTMLParser

import professional_outputs
from uniusa import (
    ability_pool,
    ability,
    final_routes,
    intake_ability,
    pathways,
    rank_ability,
    route_ability,
    scores,
    transfer,
)


ROOT = pathways.ROOT
CIP_BROWSE = pathways.SOURCES / "CIP2020-browse.html"
TEST_PERCENTILE_COLUMNS = ("sat_taker_percentile", "act_taker_percentile")
PROFESSIONAL_PROGRAMS = (
    ("MD", ROOT / "medical-schools.tsv", "MCAT", "mcat", "mcat_taker_percentile"),
    ("JD", ROOT / "law-schools.tsv", "LSAT", "lsat", "lsat_taker_percentile"),
)
PROFESSIONAL_COLUMNS = (
    "students",
    "entrance_test",
    "entrance_score",
    "entrance_taker_percentile",
)
SCHOOL_COLUMNS = (
    "school",
    "program",
    "cohort_median",
    "ability",
    "bachelors",
    *PROFESSIONAL_COLUMNS,
    "freshman_score",
    *scores.TEST_SHARE_COLUMNS,
    *TEST_PERCENTILE_COLUMNS,
    "ability_pool_ratio",
    *rank_ability.RANK_COLUMNS,
    "transfer_share",
    "transfer_score",
)
MAJOR_COLUMNS = ("school", "major") + SCHOOL_COLUMNS[1:]


class CIPTitleParser(HTMLParser):
    """Read six-digit CIP labels from the official NCES browse tree."""

    def __init__(self):
        super().__init__()
        self.in_cip_link = False
        self.text = []
        self.titles = {}

    def handle_starttag(self, tag, attrs):
        if tag == "a" and "cipdetail.aspx" in dict(attrs).get("href", ""):
            self.in_cip_link = True
            self.text = []

    def handle_data(self, data):
        if self.in_cip_link:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or not self.in_cip_link:
            return
        label = " ".join("".join(self.text).split())
        match = re.fullmatch(r"(\d{2}\.\d{4})\) (.+)", label)
        if match:
            code, title = match.groups()
            if code in self.titles:
                raise ValueError(f"Duplicate CIP title: {code}")
            self.titles[code] = title.removesuffix(".")
        self.in_cip_link = False


def load_cip_titles(path=CIP_BROWSE):
    parser = CIPTitleParser()
    parser.feed(path.read_text(encoding="utf-8"))
    if len(parser.titles) != 2_173:
        raise ValueError(f"Unexpected six-digit CIP count: {len(parser.titles):,}")
    return parser.titles


def current_split(bachelors, transfer_share):
    if transfer_share == "":
        return "", ""
    transfer = round(bachelors * transfer_share, 3)
    return round(bachelors - transfer, 3), transfer


def weighted_mean(components):
    """Mean of scored (value, count) pairs, with the weight they cover."""
    weight = sum(count for _, count in components)
    if not weight:
        return "", 0
    return sum(value * count for value, count in components) / weight, weight


def scored_components(route, paths, transfer_score):
    """Split one school's mutually exclusive routes into the measured ones."""
    freshman = [
        (route["sat_taker_percentile"], paths.get("SAT", 0)),
        (route["act_taker_percentile"], paths.get("ACT", 0)),
        (route["freshman_score"], paths.get("Service-academy nomination", 0)),
        (97.0, paths.get("Automatic class-rank guarantee", 0)),
    ]
    freshman = [
        (score, count) for score, count in freshman if score != "" and count > 0
    ]
    transfers = [(transfer_score, paths["Transfer"])] if transfer_score != "" else []
    return freshman, freshman + transfers


def assign_ranks(rows, tiebreak):
    """Sort by the cohort median and number every row carrying a score.

    Schools without a measured median keep their place on the older test-taker
    proxy, below every school the cohort scale reaches.
    """
    rows.sort(key=lambda row: (
        row["cohort_median"] == "", -(row["cohort_median"] or 0),
        row["freshman_score"] == "", -(row["freshman_score"] or 0),
        -(row["bachelors"] or 0),
    ) + tiebreak(row))
    scored = (
        row for row in rows
        if row["cohort_median"] != "" or row["freshman_score"] != ""
    )
    for rank, row in enumerate(scored, 1):
        row["rank"] = rank
    return rows


def school_rows(graduates, routes, transfer_scores, institution_routes):
    paths_by_id = {}
    for row in institution_routes:
        paths_by_id.setdefault(row["unitid"], {})[row["route"]] = row[
            "estimated_bachelors"
        ]
    test_shares = scores.test_share_means()
    blank_shares = {column: "" for column in scores.TEST_SHARE_COLUMNS}
    mean_bachelors = pathways.mean_bachelors()
    cohort_years = intake_ability.year_percentiles(transfer_scores=transfer_scores)
    cohort_medians = rank_ability.cohort_percentiles(cohort_years)
    rank_summaries, _ = rank_ability.rank_percentiles(percentiles=cohort_years)
    blank_rank = {column: "" for column in rank_ability.RANK_COLUMNS}
    pool_ratios = ability_pool.ratios(
        cohort_medians,
        mean_bachelors,
        pathways.load_population(),
    )
    rows = []
    for graduate in graduates:
        route = scores.route_fields(graduate["unitid"], routes)
        paths = paths_by_id[graduate["unitid"]]
        bachelors = graduate["bachelors_domestic"]
        transfer_count = paths["Transfer"]
        direct = bachelors - transfer_count
        share = transfer_count / bachelors
        transfer_score = transfer_scores[graduate["unitid"]]["transfer_score"]
        freshman_components, components = scored_components(
            route, paths, transfer_score
        )
        freshman_score, _ = weighted_mean(freshman_components)
        rough_ability, coverage_count = weighted_mean(components)
        coverage = coverage_count / bachelors
        if rough_ability == "":
            status = "unscored"
        elif freshman_score == "":
            status = "rough: pooled transfer-origin score only"
        else:
            status = "rough: scored freshman routes plus pooled transfer score"
        rows.append({
            "rank": "",
            "program": pathways.BACHELOR_PROGRAM,
            **{column: "" for column in PROFESSIONAL_COLUMNS},
            "cohort_median": cohort_medians.get(graduate["unitid"], ""),
            "ability": round(rough_ability, 3) if rough_ability != "" else "",
            "ability_coverage": round(coverage, 6) if coverage else "",
            **route,
            "freshman_score": round(freshman_score, 2) if freshman_score != "" else "",
            **test_shares.get(graduate["unitid"], blank_shares),
            "ability_pool_ratio": pool_ratios.get(graduate["unitid"], ""),
            **rank_summaries.get(graduate["unitid"], blank_rank),
            "transfer_score": transfer_score,
            "school_id": graduate["unitid"],
            "school": graduate["institution"],
            "state": graduate["state"],
            "bachelors": round(mean_bachelors[graduate["unitid"]], 3),
            "estimated_sat_bachelors": round(paths.get("SAT", 0), 3),
            "estimated_act_bachelors": round(paths.get("ACT", 0), 3),
            "estimated_open_admission_bachelors": round(
                paths.get("Open admission", 0), 3
            ),
            "estimated_automatic_rank_bachelors": round(
                paths.get("Automatic class-rank guarantee", 0), 3
            ),
            "estimated_recruited_athlete_bachelors": round(
                paths.get("Recruited athletics", 0), 3
            ),
            "estimated_audition_portfolio_bachelors": round(
                paths.get("Audition or portfolio", 0), 3
            ),
            "estimated_service_academy_bachelors": round(
                paths.get("Service-academy nomination", 0), 3
            ),
            "estimated_other_freshman_bachelors": round(
                paths.get("School-record review without test evidence", 0), 3
            ),
            "estimated_direct_bachelors": round(direct, 3),
            "estimated_transfer_bachelors": round(transfer_count, 3),
            "transfer_share": round(share, 6),
            "freshman_score_basis": (
                "weighted SAT, ACT, automatic-rank, and service-academy routes"
            ),
            "ability_status": status,
        })
    return assign_ranks(rows, lambda row: (row["school_id"],))


def titled_major_means(titles, wanted):
    """Mean per-major awards for the wanted schools, keeping titled CIP codes.

    Codes retired before the CIP2020 taxonomy carry no official title, so their
    mean rescales onto the school's remaining majors.
    """
    grouped = {}
    dropped = 0.0
    for row in pathways.mean_major_bachelors():
        if row["unitid"] not in wanted:
            continue
        if row["cip_code"] in titles:
            grouped.setdefault(row["unitid"], []).append(row)
        else:
            dropped += row["mean_domestic"]
    return grouped, dropped


def major_rows(schools, titles):
    by_id = {row["school_id"]: row for row in schools}
    grouped, _ = titled_major_means(titles, by_id)
    rows = []
    for unitid, majors in grouped.items():
        school = by_id[unitid]
        titled = sum(major["mean_domestic"] for major in majors)
        scale = school["bachelors"] / titled if titled else 0
        for major in majors:
            cip_code = major["cip_code"]
            bachelors = round(major["mean_domestic"] * scale, 3)
            direct, transfer = current_split(bachelors, school["transfer_share"])
            rows.append({
                "rank": "",
                "program": school["program"],
                **{column: school[column] for column in PROFESSIONAL_COLUMNS},
                "cohort_median": school["cohort_median"],
                "ability": school["ability"],
                "ability_coverage": school["ability_coverage"],
                "freshman_score": school["freshman_score"],
                **{column: school[column] for column in scores.TEST_SHARE_COLUMNS},
                "ability_pool_ratio": school["ability_pool_ratio"],
                "transfer_score": school["transfer_score"],
                "school_id": unitid,
                "school": school["school"],
                "state": school["state"],
                "cip_code": cip_code,
                "major": titles[cip_code],
                "bachelors": bachelors,
                "estimated_direct_bachelors": direct,
                "estimated_transfer_bachelors": transfer,
                "transfer_share": school["transfer_share"],
                **{column: school[column] for column in TEST_PERCENTILE_COLUMNS},
                **{column: school[column] for column in rank_ability.RANK_COLUMNS},
                "freshman_score_basis": school["freshman_score_basis"],
                "ability_status": school["ability_status"] + "; school-level",
            })
    return assign_ranks(rows, lambda row: (row["school_id"], row["cip_code"]))


def professional_rows():
    """Law and medical schools, already scored on the bachelor cohort scale.

    Both models read a school's entrance-test median onto the ability
    distribution of the undergraduates who apply, so their score means the same
    thing as a bachelor row's `cohort_median` and ranks against it directly.
    """
    blank = {column: "" for column in SCHOOL_COLUMNS}
    rows = []
    for program, path, test, score, percentile in PROFESSIONAL_PROGRAMS:
        for row in pathways.read_tsv(path):
            rows.append({
                **blank,
                "rank": "",
                "school_id": 0,
                "school": row["school"],
                "program": program,
                "cohort_median": float(row["ability"]) if row["ability"] else "",
                "students": row["students"],
                "entrance_test": test,
                "entrance_score": row[score],
                "entrance_taker_percentile": row[percentile],
            })
    return rows


def merged_school_table(schools):
    """The bachelor rows and the professional rows ranked as one list."""
    combined = assign_ranks(
        schools + professional_rows(),
        lambda row: (row["school_id"], row["school"]),
    )
    return [{column: row[column] for column in SCHOOL_COLUMNS} for row in combined]


def merge_existing_professional_tables(path=ROOT / "schools.tsv"):
    """Refresh MD/JD rows without rebuilding unchanged undergraduate estimates."""
    undergraduates = list(pathways.bachelor_rows(pathways.read_tsv(path)))
    combined = undergraduates + professional_rows()
    combined.sort(key=lambda row: (
        row["cohort_median"] == "",
        -float(row["cohort_median"] or 0),
        row["freshman_score"] == "",
        -float(row["freshman_score"] or 0),
        -float(row["bachelors"] or 0),
        row["program"],
        row["school"],
    ))
    pathways.write_tsv(
        path,
        ({column: row.get(column, "") for column in SCHOOL_COLUMNS}
         for row in combined),
    )
    return len(undergraduates), len(combined) - len(undergraduates)


def build_tables(with_majors=False):
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    admissions = ability.load_admissions()
    institution_routes = final_routes.institution_route_rows(
        graduates,
        admissions,
        ability.load_characteristics(),
        pathways.load_population(),
    )
    detailed_schools = school_rows(
        graduates,
        scores.route_lookup(graduates),
        transfer.destination_scores(institution_routes, graduates),
        institution_routes,
    )
    return detailed_schools, major_table(detailed_schools) if with_majors else []


def major_table(detailed_schools):
    """Per-major rows, checked against the school totals they were split from."""
    detailed_majors = major_rows(detailed_schools, load_cip_titles())
    major_counts = Counter()
    for row in detailed_majors:
        major_counts[row["school_id"]] += row["bachelors"]
    unreconciled = [
        row["school"] for row in detailed_schools
        if abs(major_counts[row["school_id"]] - row["bachelors"]) > 0.5
    ]
    if unreconciled:
        raise ValueError(
            f"{len(unreconciled):,} schools do not reconcile with their majors: "
            + ", ".join(unreconciled[:3])
        )
    return [
        {column: row[column] for column in MAJOR_COLUMNS}
        for row in detailed_majors
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--majors", action="store_true", help="also write the unused majors.tsv"
    )
    parser.add_argument(
        "--professionals-only",
        action="store_true",
        help="refresh MD/JD outputs and merge them into the existing schools.tsv",
    )
    args = parser.parse_args()
    if args.professionals_only:
        professional_outputs.main()
        undergraduates, professionals = merge_existing_professional_tables()
        print(f"wrote {undergraduates:,} undergraduate and {professionals:,} "
              "professional schools")
        return
    detailed, majors = build_tables(args.majors)
    schools = [
        {column: row[column] for column in SCHOOL_COLUMNS} for row in detailed
    ]
    pathways.write_tsv(ROOT / "schools.tsv", schools)
    route_ability.main()
    professional_outputs.main()
    merged = merged_school_table(detailed)
    pathways.write_tsv(ROOT / "schools.tsv", merged)
    target = f"{len(schools):,} undergraduate and {len(merged) - len(schools):,} " \
             f"professional schools"
    if args.majors:
        pathways.write_tsv(ROOT / "majors.tsv", majors)
        target += f", and {len(majors):,} school-major rows"
    print(f"wrote {target}; using separate freshman evidence and each school's "
          f"slice of the stack-ranked transfer pool")


if __name__ == "__main__":
    main()
