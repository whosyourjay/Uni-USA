#!/usr/bin/env python3
"""Collect the test-evidence figures behind schools.tsv into one JSON blob."""

import csv
import json
import re
from collections import Counter

from uniusa import ability, pathways, scores

RANK_BAND = 200
TEMPLATE = pathways.ROOT / "assets" / "test_evidence_template.html"
REPORT_PAGE = pathways.ROOT / "test_evidence.html"


def cohort_rows(admissions, schools, size):
    """Per-year test evidence for the top `size` schools of the ranking."""
    cohort = [row["unitid"] for row in schools[:size]]
    rows = []
    for year, table in admissions.items():
        totals = Counter()
        for unitid in cohort:
            admission = table.get(unitid, {})
            sat = pathways.number(admission.get("SATNUM"))
            act = pathways.number(admission.get("ACTNUM"))
            entrants = pathways.number(admission.get("ENRLT"))
            if entrants <= 0 or sat + act <= 0:
                continue
            totals["schools"] += 1
            totals["entrants"] += entrants
            totals["sat"] += sat
            totals["act"] += act
            totals["unscored"] += max(0, entrants - sat - act)
        rows.append({"year": year, "cohort": size, **totals})
    return rows


def school_rows(admissions):
    """Every ranked school with its reporting history and unscored estimate."""
    directory = pathways.load_directory()
    by_name = {row["INSTNM"]: unitid for unitid, row in directory.items()}
    with open("schools.tsv", encoding="utf-8", newline="") as source:
        ranked = pathways.bachelor_rows(csv.DictReader(source, delimiter="\t"))
    rows = []
    for position, row in enumerate(ranked, 1):
        unitid = by_name.get(row["school"])
        reported = [
            year for year, table in admissions.items()
            if pathways.number(table.get(unitid, {}).get("SATNUM"))
            + pathways.number(table.get(unitid, {}).get("ACTNUM")) > 0
        ]
        bachelors = float(row["bachelors"])
        unscored = row["no_test_pct"]
        rows.append({
            "position": position,
            "unitid": unitid,
            "school": row["school"],
            "bachelors": bachelors,
            "years": len(reported),
            "policy": ability.policy_label(admissions[2023].get(unitid, {})),
            "share": float(unscored) / 100 if unscored != "" else None,
        })
    return rows


def band_rows(schools):
    """Share of each rank band that never reports a submitter count."""
    bands = {}
    for row in schools:
        start = (row["position"] - 1) // RANK_BAND * RANK_BAND
        band = bands.setdefault(start, {"start": start + 1, "schools": 0, "blank": 0})
        band["schools"] += 1
        band["blank"] += row["share"] is None
    return [bands[start] for start in sorted(bands)]


def render(report, template=None):
    """Fill the page template, refusing to ship charts with no series behind them."""
    if template is None:
        template = TEMPLATE.read_text(encoding="utf-8")
    missing = sorted(set(re.findall(r"DATA\.(\w+)", template)) - set(report))
    if missing:
        raise ValueError(f"template reads fields the report lacks: {missing}")
    return template.replace("__DATA__", json.dumps(report, separators=(",", ":")))


def main():
    admissions = {
        year: ability.load_admissions(year) for year in scores.ADMISSION_YEARS
    }
    schools = school_rows(admissions)
    blank = [row for row in schools if row["share"] is None]
    report = {
        "hundred": cohort_rows(admissions, schools, 100),
        "ten": cohort_rows(admissions, schools, 10),
        "bands": band_rows(schools),
        "top": schools[:10],
        "heavy": sorted(
            (row for row in schools[:100] if row["share"] and row["share"] > 0.25),
            key=lambda row: -row["share"],
        ),
        "totals": {
            "schools": len(schools),
            "blank": len(blank),
            "blank_awards": sum(row["bachelors"] for row in blank),
            "first_blank": min(row["position"] for row in blank),
            "awards": sum(row["bachelors"] for row in schools),
        },
    }
    REPORT_PAGE.write_text(render(report), encoding="utf-8")
    latest = report["hundred"][-1]
    print(
        f"wrote {REPORT_PAGE.name}: top 100 reporting {latest['schools']} schools in "
        f"{latest['year']} at {(latest['sat'] + latest['act']) / latest['entrants']:.2f} "
        f"submissions per entrant; first blank at rank "
        f"{report['totals']['first_blank']:,}"
    )


if __name__ == "__main__":
    main()
