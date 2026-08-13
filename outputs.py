#!/usr/bin/env python3
"""Build the canonical school and major tables for the endpoint model."""

import argparse
import re
from collections import Counter
from html.parser import HTMLParser

import ability
import class_rank
import final_routes
import pathways
import scores
import transfer


ROOT = pathways.ROOT
CIP_BROWSE = pathways.SOURCES / "CIP2020-browse.html"
TEST_PERCENTILE_COLUMNS = tuple(
    column
    for year in scores.ADMISSION_YEARS
    for column in (
        f"sat_taker_percentile_{year}",
        f"act_taker_percentile_{year}",
    )
)
SCHOOL_COLUMNS = (
    "school",
    "ability",
    "bachelors",
    "freshman_score",
    "satnum_2019",
    "actnum_2019",
    *TEST_PERCENTILE_COLUMNS,
    "class_rank_percentile_2019",
    "transfer_share",
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


def school_rows(graduates, admissions, routes, transfer_score, institution_routes):
    paths_by_id = {}
    for row in institution_routes:
        paths_by_id.setdefault(row["unitid"], {})[row["route"]] = row[
            "estimated_bachelors"
        ]
    rows = []
    for graduate in graduates:
        route = scores.route_fields(graduate["unitid"], routes)
        admission = admissions.get(graduate["unitid"])
        paths = paths_by_id[graduate["unitid"]]
        bachelors = graduate["bachelors_domestic"]
        transfer_count = paths["Transfer"]
        direct = bachelors - transfer_count
        share = transfer_count / bachelors
        freshman_components = [
            (route["sat_taker_percentile_mean_2019_2023"], paths.get("SAT", 0)),
            (route["act_taker_percentile_mean_2019_2023"], paths.get("ACT", 0)),
            (route["freshman_score"], paths.get("Service-academy nomination", 0)),
            (97.0, paths.get("Automatic class-rank guarantee", 0)),
        ]
        freshman_components = [
            (score, count)
            for score, count in freshman_components
            if score != "" and count > 0
        ]
        freshman_weight = sum(count for _, count in freshman_components)
        freshman_score = (
            sum(score * count for score, count in freshman_components)
            / freshman_weight
            if freshman_weight else ""
        )
        components = freshman_components + [(transfer_score, transfer_count)]
        coverage_count = sum(count for _, count in components)
        coverage = coverage_count / bachelors
        rough_ability = (
            sum(value * count for value, count in components) / coverage_count
            if coverage_count
            else ""
        )
        if rough_ability == "":
            status = "unscored"
        elif freshman_score == "":
            status = "rough: pooled transfer-origin score only"
        else:
            status = "rough: scored freshman routes plus pooled transfer score"
        rows.append({
            "rank": "",
            "ability": round(rough_ability, 3) if rough_ability != "" else "",
            "ability_coverage": round(coverage, 6) if coverage else "",
            **route,
            "freshman_score": round(freshman_score, 2) if freshman_score != "" else "",
            "satnum_2019": (
                pathways.number(admission.get("SATNUM")) if admission else ""
            ),
            "actnum_2019": (
                pathways.number(admission.get("ACTNUM")) if admission else ""
            ),
            "class_rank_percentile_2019": "",
            "transfer_score": transfer_score if share != "" and share > 0 else "",
            "school_id": graduate["unitid"],
            "school": graduate["institution"],
            "state": graduate["state"],
            "bachelors": bachelors,
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
    rows.sort(key=lambda row: (
        row["ability"] == "", -(row["ability"] or 0), -row["bachelors"],
        row["school_id"],
    ))
    for rank, row in enumerate((row for row in rows if row["ability"] != ""), 1):
        row["rank"] = rank
    return rows


def major_completions():
    rows = []
    for row in pathways.zip_rows("C2023_A.zip"):
        if (
            pathways.number(row["MAJORNUM"]) == 1
            and pathways.number(row["AWLEVEL"]) == 5
            and row["CIPCODE"].strip() != "99"
        ):
            domestic = pathways.number(row["CTOTALT"]) - pathways.number(
                row["CNRALT"]
            )
            if domestic > 0:
                rows.append((
                    pathways.number(row["UNITID"]),
                    row["CIPCODE"].strip(),
                    domestic,
                ))
    return rows


def major_rows(schools, titles):
    by_id = {row["school_id"]: row for row in schools}
    rows = []
    for unitid, cip_code, bachelors in major_completions():
        school = by_id.get(unitid)
        if school is None:
            continue
        if cip_code not in titles:
            raise ValueError(f"Missing official CIP title: {cip_code}")
        direct, transfer = current_split(bachelors, school["transfer_share"])
        rows.append({
            "rank": "",
            "ability": school["ability"],
            "ability_coverage": school["ability_coverage"],
            "freshman_score": school["freshman_score"],
            "satnum_2019": school["satnum_2019"],
            "actnum_2019": school["actnum_2019"],
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
            "class_rank_percentile_2019": school[
                "class_rank_percentile_2019"
            ],
            "freshman_score_basis": school["freshman_score_basis"],
            "ability_status": school["ability_status"] + "; school-level",
        })
    rows.sort(key=lambda row: (
        row["ability"] == "", -(row["ability"] or 0), -row["bachelors"],
        row["school_id"], row["cip_code"],
    ))
    for rank, row in enumerate((row for row in rows if row["ability"] != ""), 1):
        row["rank"] = rank
    return rows


def build_tables():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    _, transfer_summary = transfer.build_transfer_tables()
    transfer_score = next(
        row["weighted_median_freshman_score"]
        for row in transfer_summary
        if row["origin_type"] == "All origins"
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
        admissions,
        scores.route_lookup(graduates),
        transfer_score,
        institution_routes,
    )
    target_ids = {
        row["school_id"] for row in class_rank.top_sample_rows(detailed_schools)
    }
    rank_scores = class_rank.score_lookup(graduates, target_ids)
    for row in detailed_schools:
        if row["school_id"] in rank_scores:
            row["class_rank_percentile_2019"] = round(
                rank_scores[row["school_id"]]["class_rank_mean"], 2
            )
    detailed_majors = major_rows(detailed_schools, load_cip_titles())
    school_counts = {
        row["school_id"]: row["bachelors"] for row in detailed_schools
    }
    major_counts = Counter()
    for row in detailed_majors:
        major_counts[row["school_id"]] += row["bachelors"]
    if school_counts != major_counts:
        raise ValueError("School and major domestic bachelor counts do not reconcile")
    schools = [
        {column: row[column] for column in SCHOOL_COLUMNS}
        for row in detailed_schools
    ]
    majors = [
        {column: row[column] for column in MAJOR_COLUMNS}
        for row in detailed_majors
    ]
    return schools, majors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schools-only", action="store_true")
    args = parser.parse_args()
    schools, majors = build_tables()
    pathways.write_tsv(ROOT / "schools.tsv", schools)
    if not args.schools_only:
        pathways.write_tsv(ROOT / "majors.tsv", majors)
    target = f"{len(schools):,} schools"
    if not args.schools_only:
        target += f" and {len(majors):,} school-major rows"
    print(f"wrote {target}; using separate freshman evidence and the pooled transfer-origin score")


if __name__ == "__main__":
    main()
