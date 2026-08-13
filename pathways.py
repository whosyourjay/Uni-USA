#!/usr/bin/env python3
"""Build final-bachelor institution weights and graduate pathway mixtures."""

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
DERIVED = ROOT / "derived"
ENTRY_LEVELS = {4: "first_time", 19: "transfer"}
OM_COHORTS = {10: "direct_full_time", 20: "direct_part_time",
              30: "transfer_full_time", 40: "transfer_part_time"}
LEVEL_NAMES = {1: "four-or-more-year", 2: "two-to-four-year", 3: "under-two-year"}
CONTROL_NAMES = {1: "public", 2: "private nonprofit", 3: "private for-profit"}


def number(value):
    value = (value or "").strip()
    return int(value) if value not in {"", "."} else 0


def zip_rows(filename, member=None):
    with zipfile.ZipFile(SOURCES / filename) as archive:
        if member is None:
            names = [name for name in archive.namelist()
                     if name.lower().endswith(".csv") and "_rv." not in name.lower()]
            if len(names) != 1:
                raise ValueError(f"Expected one primary CSV in {filename}: {names}")
            member = names[0]
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            yield from csv.DictReader(text)


def load_population():
    path = SOURCES / "nc-est2023-agesex-res.csv"
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if number(row["SEX"]) == 0 and number(row["AGE"]) == 18:
                return number(row["POPESTIMATE2023"])
    raise ValueError("Census age-18 row not found")


def load_directory():
    return {number(row["UNITID"]): row for row in zip_rows("HD2023.zip")}


def load_completions():
    completions = {}
    for row in zip_rows("C2023_A.zip"):
        if (row["CIPCODE"].strip() == "99" and number(row["MAJORNUM"]) == 1
                and number(row["AWLEVEL"]) == 5):
            unitid = number(row["UNITID"])
            if unitid in completions:
                raise ValueError(f"Duplicate bachelor's total for {unitid}")
            total = number(row["CTOTALT"])
            completions[unitid] = {
                "bachelors_all": total,
                "bachelors_domestic": total - number(row["CNRALT"]),
            }
    return completions


def load_outcomes():
    outcomes = defaultdict(dict)
    for row in zip_rows("OM2023.zip"):
        cohort = number(row["OMCHRT"])
        if cohort in OM_COHORTS:
            outcomes[number(row["UNITID"])][cohort] = {
                "cohort": number(row["OMACHRT"]),
                "bachelors": number(row["OMBACH8"]),
            }
    return outcomes


def load_enrollment():
    enrollment = defaultdict(dict)
    for row in zip_rows("EFFY2024.zip"):
        level = number(row["EFFYALEV"])
        if level in ENTRY_LEVELS:
            total = number(row["EFYTOTLT"])
            enrollment[number(row["UNITID"])][level] = {
                "all": total,
                "domestic": total - number(row["EFYNRALT"]),
            }
    return enrollment


def om_sum(outcomes, unitid, cohorts, field):
    return sum(outcomes.get(unitid, {}).get(code, {}).get(field, 0) for code in cohorts)


def graduate_rows(directory, completions, outcomes, enrollment):
    rows = []
    for unitid, awards in completions.items():
        if awards["bachelors_domestic"] <= 0:
            continue
        institution = directory.get(unitid, {})
        direct_bach = om_sum(outcomes, unitid, (10, 20), "bachelors")
        transfer_bach = om_sum(outcomes, unitid, (30, 40), "bachelors")
        direct_cohort = om_sum(outcomes, unitid, (10, 20), "cohort")
        transfer_cohort = om_sum(outcomes, unitid, (30, 40), "cohort")
        route_total = direct_bach + transfer_bach
        row = {
            "unitid": unitid,
            "institution": institution.get("INSTNM", ""),
            "state": institution.get("STABBR", ""),
            "institution_level": LEVEL_NAMES.get(number(institution.get("ICLEVEL")), "unknown"),
            "control": CONTROL_NAMES.get(number(institution.get("CONTROL")), "unknown"),
            **awards,
            "direct_bachelors_8yr": direct_bach,
            "transfer_bachelors_8yr": transfer_bach,
            "transfer_share_bachelors_8yr": transfer_bach / route_total if route_total else "",
            "direct_entering_cohort": direct_cohort,
            "transfer_entering_cohort": transfer_cohort,
            "direct_bachelor_rate_8yr": direct_bach / direct_cohort if direct_cohort else "",
            "transfer_bachelor_rate_8yr": transfer_bach / transfer_cohort if transfer_cohort else "",
        }
        for level, label in ENTRY_LEVELS.items():
            values = enrollment.get(unitid, {}).get(level, {"all": 0, "domestic": 0})
            row[label + "_entrants_all"] = values["all"]
            row[label + "_entrants_domestic"] = values["domestic"]
        rows.append(row)
    return sorted(rows, key=lambda row: (row["institution"], row["unitid"]))


def cohort_pathway_rows(population, rows):
    domestic = sum(row["bachelors_domestic"] for row in rows)
    direct = sum(row["direct_bachelors_8yr"] for row in rows)
    transfer = sum(row["transfer_bachelors_8yr"] for row in rows)
    if domestic > population:
        raise ValueError("Bachelor flow exceeds the age-18 population")
    if direct + transfer == 0:
        raise ValueError("No graduate route observations")

    # First subtract the bachelor flow from the complete age-18 population. Then
    # split only the bachelor portion using the Outcome Measures graduate mix.
    no_bachelor = population - domestic
    transfer_estimate = round(domestic * transfer / (direct + transfer))
    direct_estimate = domestic - transfer_estimate
    values = [
        ("No bachelor's degree", no_bachelor, "residual"),
        ("Bachelor's, no prior college on entry to final institution", direct_estimate,
         "IPEDS Outcome Measures route share"),
        ("Bachelor's, prior college before final institution", transfer_estimate,
         "IPEDS Outcome Measures route share"),
    ]
    return [
        {
            "path": path,
            "people": people,
            "share_age18": people / population,
            "construction": construction,
        }
        for path, people, construction in values
    ]


def level_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["institution_level"]].append(row)
    output = []
    for level in ("four-or-more-year", "two-to-four-year", "under-two-year", "unknown"):
        group = groups[level]
        if not group:
            continue
        direct = sum(row["direct_bachelors_8yr"] for row in group)
        transfer = sum(row["transfer_bachelors_8yr"] for row in group)
        output.append({
            "institution_level": level,
            "institutions": len(group),
            "bachelors_domestic": sum(row["bachelors_domestic"] for row in group),
            "om_direct_bachelors": direct,
            "om_transfer_bachelors": transfer,
            "om_transfer_share_bachelors": transfer / (direct + transfer) if direct + transfer else "",
        })
    return output


def write_tsv(path, rows):
    rows = list(rows)
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    population = load_population()
    completions = load_completions()
    rows = graduate_rows(load_directory(), completions, load_outcomes(), load_enrollment())
    write_tsv(DERIVED / "institution_graduates.tsv", rows)
    write_tsv(DERIVED / "cohort_pathways.tsv",
              cohort_pathway_rows(population, rows))
    write_tsv(DERIVED / "graduate_pathways_by_level.tsv", level_rows(rows))
    print(f"wrote {len(rows):,} bachelor-awarding institutions to {DERIVED}")


if __name__ == "__main__":
    main()
