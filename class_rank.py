#!/usr/bin/env python3
"""Score a fixed school sample's Common Data Set class-rank distributions.

Match a school in the CDS repository index to its IPEDS institution, read
section C10 out of the downloaded document, and cache one row per school in a
derived table.  Downloading and parsing live in `cds_documents` and `cds_c10`.
"""

import argparse
import csv
from difflib import SequenceMatcher
import re

import ability
import cds_c10
import cds_documents
import pathways


SCHOOL_TABLE = pathways.ROOT / "schools.tsv"
RANK_TABLE = pathways.DERIVED / "class_rank.tsv"
RANK_TABLE_COLUMNS = {
    "unitid": lambda value: int(value) if value else "",
    "class_rank_mean": lambda value: float(value) if value else "",
}


def normalize_school(name):
    name = name.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", name).split())


def document_identity_matches(school, text):
    """Reject repository links that point to a different institution."""
    return normalize_school(school) in normalize_school(text[:6000])


def top_sample_rows(rows, count=10):
    """Top freshman-score schools, then top nonduplicate ability schools."""
    rows = list(rows)
    freshman = sorted(
        (row for row in rows if row["freshman_score"] != ""),
        key=lambda row: (-float(row["freshman_score"]), row["school"]),
    )[:count]
    used = {row["school"] for row in freshman}
    ability_rows = sorted(
        (
            row for row in rows
            if row["ability"] != "" and row["school"] not in used
        ),
        key=lambda row: (-float(row["ability"]), row["school"]),
    )[:count]
    return freshman + ability_rows


def top_sample_from_tsv(path=SCHOOL_TABLE):
    with path.open(encoding="utf-8", newline="") as source:
        return top_sample_rows(csv.DictReader(source, delimiter="\t"))


def target_repository_rows(repository, targets):
    by_name = {normalize_school(row["repository_school"]): row for row in repository}
    return [
        by_name[normalize_school(target["school"])]
        for target in targets
        if normalize_school(target["school"]) in by_name
    ]


def match_school(name, graduates):
    normalized = normalize_school(name)
    exact = [
        row for row in graduates
        if normalize_school(row["institution"]) == normalized
    ]
    if len(exact) == 1:
        return exact[0]
    prefixed = [
        row for row in graduates
        if normalize_school(row["institution"]).startswith(normalized + " ")
    ]
    on_campus = [
        row for row in prefixed
        if not {"digital", "online"} & set(normalize_school(row["institution"]).split())
    ]
    if len(on_campus) == 1:
        return on_campus[0]
    candidates = sorted(
        (
            (
                SequenceMatcher(
                    None, normalized, normalize_school(row["institution"])
                ).ratio(),
                row,
            )
            for row in graduates
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    if candidates[0][0] >= 0.94 and candidates[0][0] - candidates[1][0] >= 0.03:
        return candidates[0][1]
    return None


def source_c10(source):
    """Parse one repository document, returning its C10 fields and status."""
    path = cds_documents.existing_document(source)
    if path is None:
        return path, None, "download failed"
    text = cds_documents.document_text(path)
    if not (
        source["repository_school"] in cds_documents.LOCAL_SOURCE_OVERRIDES
        or document_identity_matches(source["repository_school"], text)
    ):
        return path, None, "source identity mismatch"
    result = cds_c10.extract_c10(text)
    if result is None:
        return path, None, "downloaded; C10 unavailable"
    if result["class_rank_mean"] == "":
        return path, result, "partial C10; insufficient for mean"
    return path, result, "scored"


def score_lookup(graduates, targets, admissions=None):
    """C10 statistics for the target schools, keyed by IPEDS institution."""
    rows = read_rank_table()
    if not table_covers(rows, targets):
        rows = build_rank_table(targets, graduates, admissions)
        pathways.write_tsv(RANK_TABLE, rows)
    wanted = {target["school_id"] for target in targets}
    return {
        row["unitid"]: row
        for row in rows
        if row["unitid"] in wanted and row["class_rank_mean"] != ""
    }


def read_rank_table(path=RANK_TABLE):
    return pathways.read_tsv(path, RANK_TABLE_COLUMNS) if path.exists() else []


def table_covers(rows, targets):
    """Whether the derived table already reports every target school."""
    scored = {normalize_school(row["school"]) for row in rows}
    return all(normalize_school(target["school"]) in scored for target in targets)


def build_rank_table(targets, graduates=None, admissions=None, repository=None,
                     year=cds_documents.CDS_YEAR):
    """Score the repository documents for the targets, one row per school."""
    if graduates is None:
        graduates = load_graduates()
    if admissions is None:
        admissions = ability.load_admissions()
    if repository is None:
        repository = target_repository_rows(
            cds_documents.repository_rows(year=year), targets
        )
    rows = scored_rows(repository, graduates, admissions)
    indexed = {normalize_school(row["repository_school"]) for row in repository}
    for target in targets:
        if normalize_school(target["school"]) not in indexed:
            rows.append({
                "unitid": "",
                "school": target["school"],
                "repository_school": "",
                "cds_year": year,
                **cds_c10.EMPTY_C10,
                "rank_reporting_freshmen_estimate": "",
                "bachelors_2023": target["bachelors"],
                "source_url": "",
                "source_file": "",
                "status": f"not indexed for {year}",
            })
    return rows


def scored_rows(repository, graduates, admissions):
    output = []
    for source in repository:
        path, result, status = source_c10(source)
        school = match_school(source["repository_school"], graduates)
        admission = admissions.get(school["unitid"], {}) if school else {}
        reporting = result.get("rank_reporting_pct") if result else None
        entrants = pathways.number(admission.get("ENRLT"))
        output.append({
            "unitid": school["unitid"] if school else "",
            "school": school["institution"] if school else source["repository_school"],
            "repository_school": source["repository_school"],
            "cds_year": source["cds_year"],
            **(result or cds_c10.EMPTY_C10),
            "rank_reporting_freshmen_estimate": (
                entrants * reporting / 100 if entrants and reporting is not None else ""
            ),
            "bachelors_2023": school["bachelors_domestic"] if school else "",
            "source_url": source["source_url"],
            "source_file": str(path.relative_to(pathways.ROOT)) if path else "",
            "status": status,
        })
    return output


def load_graduates():
    return pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.fetch and not cds_documents.REPOSITORY_HTML.exists():
        cds_documents.fetch_repository_index()
    targets = top_sample_from_tsv()
    repository = target_repository_rows(cds_documents.repository_rows(), targets)
    failures = cds_documents.fetch_all(repository, args.workers) if args.fetch else {}
    fetched = len(repository) - len(failures) if args.fetch else 0
    rows = build_rank_table(targets, repository=repository)
    pathways.write_tsv(RANK_TABLE, rows)
    scored = [row for row in rows if row["status"] == "scored"]
    matched = [row for row in scored if row["unitid"] != ""]
    bachelors = sum(row["bachelors_2023"] for row in matched)
    print(
        f"targeted {len(targets):,}; indexed {len(repository):,}; "
        f"fetched this run {fetched:,}; "
        f"scored {len(scored):,}; matched {len(matched):,} institutions with "
        f"{bachelors:,.0f} domestic bachelor's awards"
    )
    if failures:
        print(f"download failures: {len(failures):,}")


if __name__ == "__main__":
    main()
