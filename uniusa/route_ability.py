#!/usr/bin/env python3
"""Attach each American institution route to that institution's ability estimate."""

import csv

from uniusa.paths import DERIVED, ROOT

SCHOOLS = ROOT / "schools.tsv"
ROUTES = DERIVED / "institution_final_routes.tsv"
TARGET = DERIVED / "route_ability.tsv"
FAMILIES = {
    "SAT": "Exam score",
    "ACT": "Exam score",
    "Automatic class-rank guarantee": "School record",
    "School-record review without test evidence": "School record",
    "Audition or portfolio": "Review",
    "Open admission": "Talent and other",
    "Recruited athletics": "Talent and other",
    "Service-academy nomination": "Talent and other",
    "Transfer": "Transfer",
}
FIELDS = ("family", "route", "ability", "seats")


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


def rows(schools=SCHOOLS, routes=ROUTES):
    """The US model reports a school-level median, shared by its route seats."""
    ability = {row["school"]: row["cohort_median"] for row in read_rows(schools)
               if row["cohort_median"]}
    missing = set()
    for row in read_rows(routes):
        score = ability.get(row["institution"])
        if score is None:
            missing.add(row["institution"])
            continue
        route = row["route"]
        family = FAMILIES.get(route)
        if family is None:
            raise ValueError(f"unclassified US route: {route}")
        yield {"family": family, "route": route, "ability": score,
               "seats": row["estimated_bachelors"]}
    if missing:
        print(f"{len(missing):,} institutions have no measured ability")


def main():
    found = list(rows())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(found)
    print(f"wrote {len(found):,} route allocations to {TARGET}")


if __name__ == "__main__":
    main()
