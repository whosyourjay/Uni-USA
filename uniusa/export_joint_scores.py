"""Export same-cohort SAT section and total percentile tables for shared fitting."""

import csv
from collections import defaultdict

from uniusa.calibrate_tests import (
    SAT_ANNUAL_PERCENTILES,
    rounded_percentile_interval,
)
from uniusa.paths import DERIVED, SOURCES


YEAR = "2019"
COMMON = {"exam": "SAT", "year": YEAR, "pool": "SAT user group"}
SECTION_PERCENTILES = {
    "ERW": SOURCES / "sat-percentile-rw.csv",
    "Math": SOURCES / "sat-percentile-math.csv",
}


def counts_from_labels(labels):
    """Turn rounded inclusive percentile labels into bucket probabilities."""
    grouped = defaultdict(list)
    for score, label in labels.items():
        grouped[label].append(score)
    uppers = {}
    for label, scores in grouped.items():
        lower, upper = rounded_percentile_interval(label)
        scores.sort()
        width = (upper - lower) / len(scores)
        for index, score in enumerate(scores):
            uppers[score] = lower + (index + 1) * width
    rows, previous = [], 0.0
    for score, upper in sorted(uppers.items()):
        if upper < previous:
            raise ValueError("SAT percentile table is not monotone")
        rows.append((score, upper - previous))
        previous = upper
    if abs(previous - 100) > 1e-9:
        raise ValueError(f"SAT percentile table ends at {previous:g}, not 100")
    return rows


def annual_labels(path, year, expected_scores):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows or year not in rows[0]:
        raise ValueError(f"{path.name}: missing {year} column")
    score_field = next(iter(rows[0]))
    labels = {int(row[score_field]): row[year].strip() for row in rows
              if row[score_field].strip() and row[year].strip()}
    if len(labels) != expected_scores:
        raise ValueError(
            f"{path.name}: expected {expected_scores} scores for {year}, "
            f"found {len(labels)}")
    return labels


def section_labels(year=YEAR):
    return {subject: annual_labels(path, year, 61)
            for subject, path in SECTION_PERCENTILES.items()}


def total_labels(year=YEAR):
    return annual_labels(SAT_ANNUAL_PERCENTILES, year, 121)


def exported_rows():
    subject_rows = []
    for subject, labels in section_labels().items():
        subject_rows.extend(
            {**COMMON, "subject": subject, "score": score, "count": count}
            for score, count in counts_from_labels(labels)
        )
    formula_rows = [
        {**COMMON, "formula": "ERW+Math", "subject": subject,
         "weight": 1, "candidates": 100}
        for subject in ("ERW", "Math")
    ]
    total_rows = [
        {**COMMON, "formula": "ERW+Math", "total_score": score, "count": count}
        for score, count in counts_from_labels(total_labels())
    ]
    return subject_rows, formula_rows, total_rows


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, list(rows[0]), delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    DERIVED.mkdir(exist_ok=True)
    names = ("joint-score-subjects.tsv", "joint-score-formulas.tsv",
             "joint-score-totals.tsv")
    for name, rows in zip(names, exported_rows()):
        path = DERIVED / name
        write(path, rows)
        print(f"wrote {len(rows):,} rows to {path}")


if __name__ == "__main__":
    main()
