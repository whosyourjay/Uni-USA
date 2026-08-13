#!/usr/bin/env python3
"""Quantify first-time and transfer entry into U.S. four-year institutions."""

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
DERIVED = ROOT / "derived"
LEVELS = {4: "first_time", 19: "transfer", 20: "continuing"}
BANDS = ["0-10%", "10-20%", "20-50%", ">50%", "not reported/open"]
CONTROL = {1: "public", 2: "private nonprofit", 3: "private for-profit"}


def number(value):
    value = (value or "").strip()
    return int(value) if value not in {"", "."} else 0


def zip_rows(filename):
    with zipfile.ZipFile(SOURCES / filename) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Expected one CSV in {filename}, found {names}")
        with archive.open(names[0]) as raw:
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
    institutions = {}
    for row in zip_rows("HD2023.zip"):
        if number(row["ICLEVEL"]) == 1 and number(row["DEGGRANT"]) == 1:
            institutions[number(row["UNITID"])] = row
    return institutions


def load_admissions():
    return {number(row["UNITID"]): row for row in zip_rows("ADM2023.zip")}


def load_enrollment():
    enrollment = defaultdict(dict)
    for row in zip_rows("EFFY2024.zip"):
        level = number(row["EFFYALEV"])
        if level in LEVELS:
            enrollment[number(row["UNITID"])][level] = {
                "all": number(row["EFYTOTLT"]),
                "nonresident": number(row["EFYNRALT"]),
            }
    return enrollment


def level_counts(enrollment, unitid, level):
    values = enrollment.get(unitid, {}).get(level, {"all": 0, "nonresident": 0})
    return values["all"], values["all"] - values["nonresident"]


def selectivity_band(applications, admitted):
    if not applications:
        return "not reported/open"
    rate = admitted / applications
    if rate <= 0.10:
        return "0-10%"
    if rate <= 0.20:
        return "10-20%"
    if rate <= 0.50:
        return "20-50%"
    return ">50%"


def institution_rows(directory, admissions, enrollment):
    rows = []
    for unitid, institution in directory.items():
        counts = {}
        for level, label in LEVELS.items():
            counts[label + "_all"], counts[label + "_domestic"] = level_counts(
                enrollment, unitid, level
            )
        admission = admissions.get(unitid, {})
        applications = number(admission.get("APPLCN"))
        admitted = number(admission.get("ADMSSN"))
        enrolled = number(admission.get("ENRLT"))
        first_time = counts["first_time_domestic"]
        transfer = counts["transfer_domestic"]
        if not first_time + transfer:
            continue
        rows.append({
            "unitid": unitid,
            "institution": institution["INSTNM"],
            "state": institution["STABBR"],
            "control": CONTROL.get(number(institution["CONTROL"]), "other"),
            "applications": applications,
            "admitted": admitted,
            "enrolled_fall": enrolled,
            "admit_rate": admitted / applications if applications else "",
            "selectivity_band": selectivity_band(applications, admitted),
            **counts,
            "transfer_share_new_domestic": (
                transfer / (first_time + transfer) if first_time + transfer else ""
            ),
        })
    return sorted(rows, key=lambda row: (row["institution"], row["unitid"]))


def national_rows(population, enrollment, directory):
    totals = {}
    for level, label in LEVELS.items():
        pairs = [level_counts(enrollment, unitid, level) for unitid in directory]
        totals[label + "_all"] = sum(pair[0] for pair in pairs)
        totals[label + "_domestic"] = sum(pair[1] for pair in pairs)
    new_domestic = totals["first_time_domestic"] + totals["transfer_domestic"]
    values = [
        ("age_18_resident_population", population, "Census resident population, July 1, 2023"),
        ("first_time_four_year_all", totals["first_time_all"], "12-month entrants, all citizenships"),
        ("first_time_four_year_domestic", totals["first_time_domestic"], "first-time total less nonresident aliens"),
        ("first_time_share_of_age18", totals["first_time_domestic"] / population, "preliminary flow-to-cohort bridge"),
        ("age18_bottom_constant", 1 - totals["first_time_domestic"] / population, "one minus preliminary bridge"),
        ("transfer_into_four_year_all", totals["transfer_all"], "12-month entrants, all citizenships"),
        ("transfer_into_four_year_domestic", totals["transfer_domestic"], "transfer total less nonresident aliens"),
        ("transfer_share_of_new_domestic", totals["transfer_domestic"] / new_domestic, "transfer / (first-time + transfer)"),
        ("continuing_four_year_domestic", totals["continuing_domestic"], "not a new-entry route"),
    ]
    return [{"metric": key, "value": value, "definition": definition} for key, value, definition in values]


def band_rows(rows, population):
    groups = defaultdict(list)
    for row in rows:
        groups[row["selectivity_band"]].append(row)
    output = []
    for band in BANDS:
        group = groups[band]
        first_time = sum(row["first_time_domestic"] for row in group)
        transfer = sum(row["transfer_domestic"] for row in group)
        output.append({
            "selectivity_band": band,
            "institutions": len(group),
            "first_time_domestic": first_time,
            "first_time_share_age18": first_time / population,
            "transfer_domestic": transfer,
            "transfer_share_new_domestic": transfer / (first_time + transfer),
        })
    return output


def write_tsv(path, rows):
    rows = list(rows)
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    population = load_population()
    directory = load_directory()
    admissions = load_admissions()
    enrollment = load_enrollment()
    institutions = institution_rows(directory, admissions, enrollment)
    national = national_rows(population, enrollment, directory)
    write_tsv(DERIVED / "national_pathways.tsv", national)
    write_tsv(DERIVED / "selectivity_pathways.tsv", band_rows(institutions, population))
    write_tsv(DERIVED / "institution_pathways.tsv", institutions)
    write_tsv(
        DERIVED / "ultraselective_pathways.tsv",
        (row for row in institutions if row["selectivity_band"] == "0-10%"),
    )
    print(f"wrote {len(institutions):,} institutions to {DERIVED}")


if __name__ == "__main__":
    main()
