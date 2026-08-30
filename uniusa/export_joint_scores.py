"""Export same-cohort SAT section and total percentile tables for shared fitting."""

import csv
from collections import defaultdict

from uniusa.calibrate_tests import (
    ACT_PROFILE_YEARS,
    SAT_ANNUAL_PERCENTILES,
    load_act_score_distributions,
    rounded_percentile_interval,
)
from uniusa.paths import DERIVED, SOURCES


SAT_YEARS = tuple(str(year) for year in range(2016, 2026))
ACT_YEARS = tuple(str(year) for year in ACT_PROFILE_YEARS)
ACT_SECTIONS = ("English", "Math", "Reading", "Science")
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
    # The maximum possible score contains every remaining candidate even when
    # the publisher prints its inclusive percentile as a rounded ``99``.
    uppers[max(uppers)] = 100.0
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


def section_labels(year):
    return {subject: annual_labels(path, year, 61)
            for subject, path in SECTION_PERCENTILES.items()}


def total_labels(year):
    return annual_labels(SAT_ANNUAL_PERCENTILES, year, 121)


def sat_rows(year):
    common = {"exam": "SAT", "year": year, "pool": "SAT user group"}
    subject_rows = []
    for subject, labels in section_labels(year).items():
        subject_rows.extend(
            {**common, "subject": subject, "score": score, "count": count}
            for score, count in counts_from_labels(labels)
        )
    formula_rows = [
        {**common, "formula": "ERW+Math", "subject": subject,
         "weight": 1, "candidates": 100, "round_to": ""}
        for subject in ("ERW", "Math")
    ]
    total_rows = [
        {**common, "formula": "ERW+Math", "total_score": score, "count": count}
        for score, count in counts_from_labels(total_labels(year))
    ]
    return subject_rows, formula_rows, total_rows


def act_rows(year):
    common = {"exam": "ACT", "year": year, "pool": "tested graduates"}
    distributions = load_act_score_distributions(int(year))
    candidates = sum(distributions["Composite"].values())
    subject_rows = [
        {**common, "subject": subject, "score": score, "count": count}
        for subject in ACT_SECTIONS
        for score, count in sorted(distributions[subject].items())
    ]
    formula_rows = [
        {**common, "formula": "Composite", "subject": subject,
         "weight": 0.25, "candidates": candidates, "round_to": 1}
        for subject in ACT_SECTIONS
    ]
    total_rows = [
        {**common, "formula": "Composite", "total_score": score, "count": count}
        for score, count in sorted(distributions["Composite"].items())
    ]
    return subject_rows, formula_rows, total_rows


def exported_rows(sat_years=SAT_YEARS, act_years=ACT_YEARS):
    tables = ([], [], [])
    for year in sat_years:
        for output, rows in zip(tables, sat_rows(str(year))):
            output.extend(rows)
    for year in act_years:
        for output, rows in zip(tables, act_rows(str(year))):
            output.extend(rows)
    return tables


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
