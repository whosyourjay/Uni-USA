#!/usr/bin/env python3
"""Build the canonical school and major tables for the endpoint model."""

import re
from html.parser import HTMLParser

import ability
import calibrate_tests
import pathways


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


def route_lookup(graduates):
    admissions = ability.load_admissions()
    evidence = ability.ability_evidence_rows(graduates, admissions)
    components = ability.test_component_rows(evidence)
    percentiles = calibrate_tests.component_percentile_rows(components)
    return {
        (row["unitid"], row["route"]): round(
            row["estimated_route_central_test_taker_percentile"], 3
        )
        for row in calibrate_tests.route_percentile_rows(percentiles)
    }


def route_fields(unitid, routes):
    sat = routes.get((unitid, "SAT"), "")
    act = routes.get((unitid, "ACT"), "")
    labels = [name for name, value in (("SAT", sat), ("ACT", act)) if value != ""]
    return {
        "sat_taker_percentile_2019": sat,
        "act_taker_percentile_2019": act,
        "ability_status": (
            f"partial: {' and '.join(labels)} freshman route evidence"
            if labels
            else "unscored"
        ),
    }


def school_rows(graduates, routes):
    rows = []
    for graduate in graduates:
        direct, transfer = current_split(
            graduate["bachelors_domestic"],
            graduate["transfer_share_bachelors_8yr"],
        )
        rows.append({
            "rank": "",
            "ability": "",
            "school_id": graduate["unitid"],
            "school": graduate["institution"],
            "state": graduate["state"],
            "bachelors": graduate["bachelors_domestic"],
            "estimated_direct_bachelors": direct,
            "estimated_transfer_bachelors": transfer,
            "transfer_share": (
                round(graduate["transfer_share_bachelors_8yr"], 6)
                if graduate["transfer_share_bachelors_8yr"] != ""
                else ""
            ),
            **route_fields(graduate["unitid"], routes),
        })
    return sorted(rows, key=lambda row: (-row["bachelors"], row["school_id"]))


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
            "ability": "",
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
            "ability_status": school["ability_status"],
        })
    return sorted(
        rows,
        key=lambda row: (-row["bachelors"], row["school_id"], row["cip_code"]),
    )


def build_tables():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    schools = school_rows(graduates, route_lookup(graduates))
    majors = major_rows(schools, load_cip_titles())
    return schools, majors


def main():
    schools, majors = build_tables()
    pathways.write_tsv(ROOT / "schools.tsv", schools)
    pathways.write_tsv(ROOT / "majors.tsv", majors)
    print(
        f"wrote {len(schools):,} schools and {len(majors):,} school-major rows; "
        "ability remains blank until direct and transfer routes share one scale"
    )


if __name__ == "__main__":
    main()
