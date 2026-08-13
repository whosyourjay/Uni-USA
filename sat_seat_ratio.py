#!/usr/bin/env python3
"""Compare selective-school SAT q25 bars with the national SAT upper tail."""

import csv
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile

import calibrate_tests
import pathways


ROOT = Path(__file__).parent
YEARS = (2017, 2018, 2019)
SCHOOLS = {
    166683: "Massachusetts Institute of Technology",
    115409: "Harvey Mudd College",
    110404: "California Institute of Technology",
    144050: "University of Chicago",
    186131: "Princeton University",
}


def admissions(year):
    path = ROOT / "sources" / f"ADM{year}.zip"
    with ZipFile(path) as archive:
        with archive.open(f"adm{year}.csv") as source:
            rows = csv.DictReader(line.decode("utf-8-sig") for line in source)
            return {
                int(row["UNITID"]): row
                for row in rows
                if int(row["UNITID"]) in SCHOOLS
            }


def national_test_takers(year):
    path = ROOT / "sources" / f"{year}-total-group-sat-report.pdf"
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    compact = "".join(result.stdout.split())
    counts = re.findall(r"\d{1,3}(?:,\d{3}){2}", compact)
    if not counts:
        raise ValueError(f"Could not find SAT test-taker count in {path.name}")
    total = int(counts[0].replace(",", ""))
    if not 1_000_000 < total < 3_000_000:
        raise ValueError(f"Implausible SAT test-taker count: {total:,}")
    return total


def annual_rows():
    output = []
    for year in YEARS:
        table = calibrate_tests.load_sat_total_user_percentiles(year)
        total_test_takers = national_test_takers(year)
        school_rows = admissions(year)
        for unitid, school in SCHOOLS.items():
            row = school_rows[unitid]
            q25_sum = int(row["SATVR25"]) + int(row["SATMT25"])
            percentile = calibrate_tests.interpolate(table, q25_sum)
            passing = total_test_takers * (1 - percentile / 100)
            seats = int(row["ENRLT"])
            seats_above = 0.75 * seats
            output.append({
                "school": school,
                "year": year,
                "sat_q25_section_sum": q25_sum,
                "sat_q25_test_taker_percentile": round(percentile, 4),
                "sat_test_takers": total_test_takers,
                "test_takers_at_or_above_q25": round(passing),
                "first_year_seats": seats,
                "seats_at_or_above_q25": round(seats_above, 2),
                "test_takers_at_or_above_per_seat": round(
                    passing / seats_above, 2
                ),
            })
    return output


def average_rows(rows):
    output = []
    for school in SCHOOLS.values():
        values = [row for row in rows if row["school"] == school]
        result = {"school": school, "year": "2017-19 average"}
        for field in (
            "sat_q25_section_sum",
            "sat_q25_test_taker_percentile",
            "sat_test_takers",
            "test_takers_at_or_above_q25",
            "first_year_seats",
            "seats_at_or_above_q25",
            "test_takers_at_or_above_per_seat",
        ):
            result[field] = round(sum(row[field] for row in values) / len(values), 2)
        output.append(result)
    return output


def main():
    rows = annual_rows()
    pathways.write_tsv(
        ROOT / "derived" / "top_sat_q25_seat_ratios.tsv",
        rows + average_rows(rows),
    )
    for row in average_rows(rows):
        print(
            f"{row['school']}: "
            f"{row['test_takers_at_or_above_per_seat']:.2f} per seat"
        )


if __name__ == "__main__":
    main()
