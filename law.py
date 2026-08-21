#!/usr/bin/env python3
"""Score ABA law-school entering classes from their published LSAT bars."""

import re
import subprocess
from statistics import fmean

import professional

ABA_SOURCE = professional.SOURCES / "aba-law-2024.xlsx"
LSAT_SOURCE = professional.SOURCES / "lsat-percentiles-2021-2024.pdf"
OUTPUT = professional.ROOT / "law-schools.tsv"


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
            for edge in ("25th", "50th", "75th")]
    return [bar for bar in bars if bar is not None and low <= bar <= high]


def route_count(row, stem):
    return professional.numeric(row.get(f"{stem}TotalEnrollees")) or 0


def score_row(row, table, origins):
    bars = reported_bars(row, "LSAT")
    percentiles = [professional.interpolate(table, score) for score in bars]
    origin_scores = [
        professional.weighted_quantile(origins, percentile / 100)
        for percentile in percentiles
    ]
    students = professional.numeric(row.get("TotalEnrollees")) or 0
    lsat_students = route_count(row, "LSAT")
    return {
        "school": row["SchoolName"],
        "ability": round(fmean(origin_scores), 3) if origin_scores else "",
        "students": int(students),
        "lsat": round(bars[1] if len(bars) == 3 else fmean(bars), 1) if bars else "",
        "lsat_taker_percentile": round(fmean(percentiles), 3) if percentiles else "",
        "lsat_share": round(lsat_students / students, 3) if students else "",
    }


def school_rows():
    table = lsat_percentiles()
    origins = professional.bachelor_origins()
    rows = [score_row(row, table, origins) for row in aba_rows()]
    rows.sort(key=lambda row: (row["ability"] == "", -(row["ability"] or 0)))
    return rows


def main():
    rows = school_rows()
    professional.write_tsv(OUTPUT, rows)
    scored = sum(row["ability"] != "" for row in rows)
    print(f"{OUTPUT.name}: {scored}/{len(rows)} law schools scored")


if __name__ == "__main__":
    main()
