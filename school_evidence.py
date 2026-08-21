#!/usr/bin/env python3
"""Print one school's admission evidence year by year.

Usage: python3 school_evidence.py "california institute of tech"
"""

import re
import sys

import ability
import cds_c10
import cds_documents
import entering_class
import pathways
import rank_ability
import scores

COUNT_FIELDS = ("APPLCN", "ADMSSN", "ENRLT", "SATNUM", "ACTNUM")


def find_school(pattern):
    """Resolve a case-insensitive name fragment to one directory entry."""
    needle = pattern.lower()
    matches = [
        (unitid, row["INSTNM"])
        for unitid, row in pathways.load_directory().items()
        if needle in row["INSTNM"].lower()
    ]
    if not matches:
        raise SystemExit(f"no school matching {pattern!r}")
    exact = [match for match in matches if match[1].lower() == needle]
    if exact:
        return exact[0]
    if len(matches) > 1:
        names = ", ".join(name for _, name in matches[:6])
        raise SystemExit(f"{len(matches)} schools match {pattern!r}: {names}")
    return matches[0]


def consideration_rows(unitid, admissions):
    """What each year's ADM survey says the school weighs, test policy included."""
    rows = []
    for year, table in admissions.items():
        admission = table.get(unitid)
        if not admission:
            continue
        rows.append({
            "year": year,
            **{
                label: ability.CONSIDERATION_STATUS.get(
                    pathways.number(admission.get(field)), "not reported"
                )
                for field, label in ability.CONSIDERATIONS.items()
            },
        })
    return rows


def count_rows(unitid, admissions):
    """Applicant, admit, entrant and submitter counts for each admission year."""
    rows = []
    for year, table in admissions.items():
        admission = table.get(unitid)
        if not admission:
            continue
        counts = {field: pathways.number(admission.get(field)) for field in COUNT_FIELDS}
        entrants = counts["ENRLT"]
        counts["unscored"] = max(0, entrants - counts["SATNUM"] - counts["ACTNUM"])
        rows.append({"year": year, **counts})
    return rows


def print_table(title, rows, keys):
    print(f"\n{title}")
    widths = {key: max(len(key), *(len(str(row[key])) for row in rows)) for key in keys}
    print("  ".join(f"{key:>{widths[key]}}" for key in keys))
    for row in rows:
        print("  ".join(f"{str(row[key]):>{widths[key]}}" for key in keys))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    unitid, name = find_school(" ".join(sys.argv[1:]))
    admissions = {year: ability.load_admissions(year) for year in scores.ADMISSION_YEARS}
    print(f"{name} ({unitid})")

    counts = count_rows(unitid, admissions)
    print_table("Counts", counts, ("year", *COUNT_FIELDS, "unscored"))

    considerations = consideration_rows(unitid, admissions)
    labels = list(ability.CONSIDERATIONS.values())
    for label in labels:
        history = {row[label] for row in considerations}
        if len(history) == 1:
            print(f"\n{label}: {history.pop()} in every reported year")
    varying = [label for label in labels if len({r[label] for r in considerations}) > 1]
    if varying:
        print_table("Changed over time", considerations, ("year", *varying))

    print_rank_history(unitid, name)


def cds_history(school):
    """Parse every locally fetched Common Data Set for one school."""
    slug = re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")
    rows = []
    for year in sorted(cds_documents.CDS_YEAR_COLUMNS, reverse=True):
        matches = list(cds_documents.cds_directory(year).glob(f"{slug}--*"))
        if not matches:
            continue
        result = cds_c10.extract_c10(cds_documents.document_text(matches[0]))
        if result:
            rows.append({"cds_year": year, **result})
    return rows


def rank_history(unitid, school):
    """Class-rank observations: every entering class, then any fetched CDS."""
    rows = [
        {"year": f"fall {row['entering_year']}", "rank_reporting_pct": "", **row}
        for row in entering_class.school_history(unitid)
    ]
    for row in cds_history(school):
        if row["top_10_pct"]:
            rows.append({"year": row["cds_year"], **row})
    return rows


def modeled_percentile(top_10, fit):
    """Cohort percentile the fitted scale reads out of a top-decile share."""
    if not rank_ability.usable_share({"top_10_pct": top_10 or ""}):
        return float("nan")
    return rank_ability.implied_percentile(top_10, fit)


def print_rank_history(unitid, school):
    print("\nClass rank")
    rows = rank_history(unitid, school)
    if not rows:
        print("  no entering-class listing and no fetched CDS documents")
        return
    _, fit = rank_ability.rank_percentiles()
    print(f"  {'year':<9} {'top10':>6} {'top25':>6} {'rank%':>6} "
          f"{'uniform':>8} {'modeled':>8}")
    shares = ("top_10_pct", "top_25_pct", "rank_reporting_pct")
    for row in rows:
        cells = " ".join(f"{str(row[key] or '--'):>6}" for key in shares)
        print(f"  {row['year']:<9} {cells} "
              f"{row['class_rank_mean'] or float('nan'):>8.2f} "
              f"{modeled_percentile(row['top_10_pct'], fit):>8.2f}")


if __name__ == "__main__":
    main()
