"""Export SAT section and total percentile tables for shared fitting.

The total table is the 2019 SAT-user table. The locally mirrored section table
describes a recent three-year SAT-user group, so this is a useful but imperfect
cross-vintage calibration case.
"""

import csv
from collections import defaultdict

from uniusa.calibrate_tests import (
    SAT_ANNUAL_PERCENTILES,
    SAT_PERCENTILES,
    SectionPercentileParser,
    rounded_percentile_interval,
)
from uniusa.paths import DERIVED


YEAR = "2019-proxy"
COMMON = {"exam": "SAT", "year": YEAR, "pool": "SAT user group"}


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


def section_labels():
    parser = SectionPercentileParser()
    parser.feed(SAT_PERCENTILES.read_text(encoding="utf-8"))
    tables = {"ERW": {}, "Math": {}}
    for row in parser.rows:
        if len(row) == 5 and row[0].isdigit():
            score = int(row[0])
            tables["ERW"][score] = row[2]
            tables["Math"][score] = row[4]
    if any(len(table) != 61 for table in tables.values()):
        raise ValueError("incomplete SAT section percentile table")
    return tables


def total_labels(year="2019"):
    with SAT_ANNUAL_PERCENTILES.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    score_field = next(iter(rows[0]))
    labels = {int(row[score_field]): row[year].strip() for row in rows
              if row[score_field].strip() and row[year].strip()}
    if len(labels) != 121:
        raise ValueError(f"incomplete {year} SAT total percentile table")
    return labels


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
