#!/usr/bin/env python3
"""Score ABA law-school entering classes from their published LSAT bars.

A school's LSAT bar converts to a percentile among LSAT takers, and that ranking
only becomes an age-18 ability once the takers themselves are placed.  Law
publishes no feeder table naming the undergraduate schools its applicants come
from, so this builds an estimated one and reads the percentile off it:

    takers from school i  ~  bachelors_i * exp(gradient * (ability_i - 50))
    taker ability CDF     =  sum over i of school_i's own CDF, at those weights
    school's ability      =  that CDF inverted at the LSAT taker percentile

The gradient is the one measurable piece.  AAMC publishes medical applicants per
undergraduate school, so regressing log(applicants / bachelors) on school ability
measures how much faster strong schools send people to a professional entrance
exam.  Law borrows that slope, which assumes pre-law selection tilts like pre-med
selection.  Its size is the model's main assumption and worth checking against
`gradient` in the build output.

Two things this does not do.  It never uses law-school data to place law takers,
so no law input enters its own answer.  And it applies no within-school
selection: a taker from a school looks like a random graduate of it, which pulls
every score toward the school average.
"""

import re
import subprocess
from statistics import fmean

from uniusa.paths import DERIVED
from uniusa.professional import common as professional
from uniusa.professional import medicine

ABA_SOURCE = professional.SOURCES / "aba-law-2024.xlsx"
LSAT_SOURCE = professional.SOURCES / "lsat-percentiles-2021-2024.pdf"
OUTPUT = professional.ROOT / "law-schools.tsv"
ORIGIN_OUTPUT = DERIVED / "law_origins.tsv"
BARS = ("25th", "50th", "75th")


def lsat_percentiles(path=LSAT_SOURCE):
    """Hundredths percent-below table from LSAC's 2021-2024 PDF."""
    text = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True, capture_output=True, text=True,
    ).stdout
    rows = re.findall(r"^\s*(1[2-7]\d|180)\s+(\d+\.\d+)%", text, re.MULTILINE)
    table = {int(score): float(percentile) for score, percentile in rows}
    if set(table) != set(range(120, 181)):
        raise ValueError(f"Expected LSAT scores 120-180, found {len(table)}")
    return table


def aba_rows(path=ABA_SOURCE):
    values = professional.xlsx_rows(path)
    header = next(values)
    for row in values:
        yield dict(zip(header, row))


def reported_bars(row, stem, low=120, high=180):
    bars = [professional.numeric(row.get(f"All{edge}Percentile{stem}"))
            for edge in BARS]
    return [bar for bar in bars if bar is not None and low <= bar <= high]


def route_count(row, stem):
    return professional.numeric(row.get(f"{stem}TotalEnrollees")) or 0


def taker_origins():
    """Every undergraduate school with its estimated share of LSAT takers."""
    gradient = professional.application_gradient(medicine.feeder_rows())
    return professional.applicant_origins(
        professional.bachelor_origins(), gradient
    ), gradient


def score_row(row, table, mixture, ability_cache=None):
    bars = reported_bars(row, "LSAT")
    percentiles = [professional.interpolate(table, score) for score in bars]
    ability_cache = {} if ability_cache is None else ability_cache
    for percentile in percentiles:
        if percentile not in ability_cache:
            ability_cache[percentile] = mixture.quantile(percentile / 100)
    students = professional.numeric(row.get("TotalEnrollees")) or 0
    lsat_students = route_count(row, "LSAT")
    return {
        "school": row["SchoolName"],
        "ability": round(
            fmean(ability_cache[percentile] for percentile in percentiles), 3
        ) if percentiles else "",
        "students": int(students),
        "lsat": round(bars[1] if len(bars) == 3 else fmean(bars), 1) if bars else "",
        "lsat_taker_percentile": round(fmean(percentiles), 3) if percentiles else "",
        "lsat_share": round(lsat_students / students, 3) if students else "",
    }


def school_rows(aba, table, mixture):
    cache = {}
    rows = [score_row(row, table, mixture, cache) for row in aba]
    rows.sort(key=lambda row: (row["ability"] == "", -(row["ability"] or 0)))
    return rows


def main():
    table = lsat_percentiles()
    aba = list(aba_rows())
    origins, gradient = taker_origins()
    professional.write_tsv(ORIGIN_OUTPUT, (
        {"school": row["school"], "ability": row["ability"],
         "bachelors": row["bachelors"], "taker_share": round(row["applicants"], 6)}
        for row in sorted(origins, key=lambda row: -row["applicants"])
    ))
    mixture = professional.origin_mixture(origins)
    rows = school_rows(aba, table, mixture)
    professional.write_tsv(OUTPUT, rows)
    scored = sum(row["ability"] != "" for row in rows)
    print(
        f"{OUTPUT.name}: {scored}/{len(rows)} law schools scored; "
        f"gradient {gradient:.4f}/ability point; "
        f"taker pool covers {mixture.weight:.1%} of graduates"
    )


if __name__ == "__main__":
    main()
