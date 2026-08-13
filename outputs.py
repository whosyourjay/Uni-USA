#!/usr/bin/env python3
"""Build the canonical school and major tables for the endpoint model."""

import re
from collections import Counter
from html.parser import HTMLParser

import pathways
import scores
import transfer


ROOT = pathways.ROOT
CIP_BROWSE = pathways.SOURCES / "CIP2020-browse.html"
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


def school_rows(graduates, routes, transfer_score):
    rows = []
    for graduate in graduates:
        route = scores.route_fields(graduate["unitid"], routes)
        freshman_score = route["freshman_score"]
        share = graduate["transfer_share_bachelors_8yr"]
        direct, transfer = current_split(
            graduate["bachelors_domestic"],
            share,
        )
        components = []
        if share == "":
            if freshman_score != "":
                components.append((freshman_score, 1))
        else:
            if freshman_score != "":
                components.append((freshman_score, 1 - share))
            components.append((transfer_score, share))
        coverage = sum(weight for _, weight in components)
        rough_ability = (
            sum(value * weight for value, weight in components) / coverage
            if coverage
            else ""
        )
        if rough_ability == "":
            status = "unscored"
        elif share == "":
            status = "rough: freshman score; transfer share missing"
        elif freshman_score == "":
            status = "rough: pooled transfer-origin score only"
        else:
            status = "rough: freshman plus pooled transfer-origin score"
        rows.append({
            "rank": "",
            "ability": round(rough_ability, 3) if rough_ability != "" else "",
            "ability_coverage": round(coverage, 6) if coverage else "",
            "freshman_score": freshman_score,
            "transfer_score": transfer_score if share != "" and share > 0 else "",
            "school_id": graduate["unitid"],
            "school": graduate["institution"],
            "state": graduate["state"],
            "bachelors": graduate["bachelors_domestic"],
            "estimated_direct_bachelors": direct,
            "estimated_transfer_bachelors": transfer,
            "transfer_share": (
                round(share, 6)
                if graduate["transfer_share_bachelors_8yr"] != ""
                else ""
            ),
            **route,
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
            "sat_taker_percentile_2019": school["sat_taker_percentile_2019"],
            "act_taker_percentile_2019": school["act_taker_percentile_2019"],
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
    schools = school_rows(graduates, scores.route_lookup(graduates), transfer_score)
    majors = major_rows(schools, load_cip_titles())
    school_counts = {row["school_id"]: row["bachelors"] for row in schools}
    major_counts = Counter()
    for row in majors:
        major_counts[row["school_id"]] += row["bachelors"]
    if school_counts != major_counts:
        raise ValueError("School and major domestic bachelor counts do not reconcile")
    return schools, majors


def main():
    schools, majors = build_tables()
    pathways.write_tsv(ROOT / "schools.tsv", schools)
    pathways.write_tsv(ROOT / "majors.tsv", majors)
    print(
        f"wrote {len(schools):,} schools and {len(majors):,} school-major rows; "
        "using separate freshman evidence and the pooled transfer-origin score"
    )


if __name__ == "__main__":
    main()
